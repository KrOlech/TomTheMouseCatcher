/*
  TomTheMouseCatcher — FAIL-SAFE MOTOR CONTROLLER V10.1 HARD-CAPPED BACKOFF

  This firmware changes only end-stop handling relative to V9:

  1. The released electrical level of each switch is measured at startup.
     Therefore an end stop can be active LOW or active HIGH.
  2. Interrupts use CHANGE, not only FALLING.
  3. On an active end event, STEP is forced LOW and the driver is disabled
     immediately inside the ISR, preventing continued pushing.
  4. Arduino then performs one forced reverse backoff.
  5. Switch bounce from the same end cannot schedule another backoff.
  6. After recovery, movement back toward that end remains blocked.

  Normal commands:
    -3 LEFT FAST
    -1 LEFT CREEP
     1 RIGHT CREEP
     3 RIGHT FAST
   100 STOP/HOLD
   101 EMERGENCY DISABLE
   200 CLEAR LOCK/FAULT
   201 IDENTIFY
*/

#define X_EN_PIN 4
#define X_STEP_PIN 6
#define X_DIR_PIN 5

#define L_END_STOP_PIN 2
#define R_END_STOP_PIN 3

#define LEFT_DIRECTION HIGH
#define RIGHT_DIRECTION LOW

const int COMMAND_HEARTBEAT = 0;
const int COMMAND_STOP = 100;
const int COMMAND_EMERGENCY_STOP = 101;
const int COMMAND_CLEAR_FAULT = 200;
const int COMMAND_IDENTIFY = 201;

const unsigned long STEP_PULSE_US = 20;

const unsigned long FAST_INTERVAL_US = 2200;
const unsigned long CREEP_INTERVAL_US = 2500;

const unsigned long START_INTERVAL_US = 14000;
const unsigned long ACCELERATION_CHANGE_US = 500;



const unsigned long COMMAND_TIMEOUT_MS = 500;
const unsigned long NORMAL_HOLD_MS = 900;

/*
  HARD-CAPPED end-stop recovery.

  The previous firmware could execute up to 3000 release steps plus
  800 additional steps. That was unsafe and was not a valid conversion
  to camera pixels.

  V10.1 performs at most BACKOFF_TOTAL_STEPS pulses in total, including
  the pulses needed to release the switch. At 5000 us per pulse this
  lasts at most about 0.5 seconds.

  Start with 100 pulses and calibrate only during a no-animal bench test.
*/
const unsigned long BACKOFF_TOTAL_STEPS = 100;
const unsigned long BACKOFF_INTERVAL_US = 5000;

enum ControllerState {
  STATE_IDLE,
  STATE_MOVING,
  STATE_END_LOCKED,
  STATE_FAULT
};

volatile int pendingEndTrip = 0;
volatile bool backoffInProgress = false;
volatile int activeRecoveryEnd = 0;

ControllerState controllerState = STATE_IDLE;

int lockedEnd = 0;
int currentDirection = 0;

bool stepPinHigh = false;
bool motorHolding = false;

int leftReleasedLevel = HIGH;
int rightReleasedLevel = HIGH;

unsigned long lastStepChangeUs = 0;
unsigned long currentIntervalUs = START_INTERVAL_US;
unsigned long targetIntervalUs = CREEP_INTERVAL_US;
unsigned long lastCommandMs = 0;
unsigned long holdStartedMs = 0;

String serialBuffer = "";


bool leftEndActive() {
  return digitalRead(L_END_STOP_PIN) != leftReleasedLevel;
}


bool rightEndActive() {
  return digitalRead(R_END_STOP_PIN) != rightReleasedLevel;
}


void emergencyCutMotorFromISR() {
  digitalWrite(X_STEP_PIN, LOW);

  /*
    EN is active LOW in this installation.
    HIGH immediately removes commanded motor torque.
  */
  digitalWrite(X_EN_PIN, HIGH);
}


void leftEndISR() {
  if (!leftEndActive()) {
    return;
  }

  if (
    backoffInProgress
    && activeRecoveryEnd == -1
  ) {
    return;
  }

  emergencyCutMotorFromISR();
  pendingEndTrip = -1;
}


void rightEndISR() {
  if (!rightEndActive()) {
    return;
  }

  if (
    backoffInProgress
    && activeRecoveryEnd == 1
  ) {
    return;
  }

  emergencyCutMotorFromISR();
  pendingEndTrip = 1;
}


void resetPulseState() {
  digitalWrite(X_STEP_PIN, LOW);
  stepPinHigh = false;
  currentDirection = 0;
  currentIntervalUs = START_INTERVAL_US;
  targetIntervalUs = CREEP_INTERVAL_US;
}


void enableMotorHardware() {
  digitalWrite(X_EN_PIN, LOW);
  motorHolding = false;
}


void disableMotorHardware() {
  resetPulseState();
  digitalWrite(X_EN_PIN, HIGH);
  motorHolding = false;
}


void holdMotor() {
  resetPulseState();
  digitalWrite(X_EN_PIN, LOW);
  motorHolding = true;
  holdStartedMs = millis();
}


void setPhysicalDirection(int direction) {
  digitalWrite(
    X_DIR_PIN,
    direction < 0 ? LEFT_DIRECTION : RIGHT_DIRECTION
  );
}


void pulseBackoffStep() {
  digitalWrite(X_STEP_PIN, HIGH);
  delayMicroseconds(STEP_PULSE_US);
  digitalWrite(X_STEP_PIN, LOW);

  if (BACKOFF_INTERVAL_US > STEP_PULSE_US) {
    delayMicroseconds(
      BACKOFF_INTERVAL_US - STEP_PULSE_US
    );
  }
}


void enterFault(const __FlashStringHelper* message) {
  backoffInProgress = false;
  activeRecoveryEnd = 0;
  disableMotorHardware();
  controllerState = STATE_FAULT;

  Serial.print(F("FAULT: "));
  Serial.println(message);
}


void performForcedBackoff(int endSide) {
  noInterrupts();
  pendingEndTrip = 0;
  backoffInProgress = true;
  activeRecoveryEnd = endSide;
  interrupts();

  resetPulseState();
  lockedEnd = endSide;

  int awayDirection = endSide < 0 ? 1 : -1;

  setPhysicalDirection(awayDirection);
  enableMotorHardware();
  delayMicroseconds(30);

  if (endSide < 0) {
    Serial.println(F(
      "left end detected: HARD-CAPPED RIGHT BACKOFF"
    ));
  } else {
    Serial.println(F(
      "right end detected: HARD-CAPPED LEFT BACKOFF"
    ));
  }

  unsigned long totalBackoffSteps = 0;

  /*
    One absolute pulse budget. The release movement and the extra clearance
    movement share the same 100-pulse maximum.
  */
  while (totalBackoffSteps < BACKOFF_TOTAL_STEPS) {
    bool oppositeActive =
        endSide < 0
        ? rightEndActive()
        : leftEndActive();

    if (oppositeActive) {
      enterFault(F(
        "opposite end active during capped backoff"
      ));
      return;
    }

    pulseBackoffStep();
    totalBackoffSteps++;
  }

  bool originalStillActive =
      endSide < 0
      ? leftEndActive()
      : rightEndActive();

  /*
    If 100 pulses were not enough to release the original switch, stop and
    latch a fault. Never continue blindly across the maze.
  */
  if (originalStillActive) {
    enterFault(F(
      "end switch still active after capped backoff"
    ));
    return;
  }

  holdMotor();
  controllerState = STATE_END_LOCKED;

  noInterrupts();
  pendingEndTrip = 0;
  backoffInProgress = false;
  activeRecoveryEnd = 0;
  interrupts();

  Serial.print(F("backoff complete: total steps="));
  Serial.println(totalBackoffSteps);

  if (endSide < 0) {
    Serial.println(F("left backoff complete: LEFT LOCKED"));
  } else {
    Serial.println(F("right backoff complete: RIGHT LOCKED"));
  }
}

void processPendingEndTrip() {
  int trip;

  noInterrupts();
  trip = pendingEndTrip;
  pendingEndTrip = 0;
  interrupts();

  if (
    trip == 0
    || controllerState == STATE_FAULT
    || backoffInProgress
  ) {
    return;
  }

  performForcedBackoff(trip);
}


unsigned long intervalForCommand(int command) {
  return abs(command) >= 3
      ? FAST_INTERVAL_US
      : CREEP_INTERVAL_US;
}


void startMovement(int command) {
  if (
    controllerState == STATE_FAULT
    || backoffInProgress
  ) {
    return;
  }

  int direction = command < 0 ? -1 : 1;

  if (controllerState == STATE_END_LOCKED) {
    int allowedDirection =
        lockedEnd < 0 ? 1 : -1;

    if (direction != allowedDirection) {
      holdMotor();
      controllerState = STATE_END_LOCKED;

      if (lockedEnd < 0) {
        Serial.println(F("LEFT command blocked after end hit"));
      } else {
        Serial.println(F("RIGHT command blocked after end hit"));
      }

      return;
    }

    lockedEnd = 0;
    controllerState = STATE_IDLE;
    Serial.println(F("end lock cleared by inward command"));
  }

  if (direction < 0 && leftEndActive()) {
    performForcedBackoff(-1);
    return;
  }

  if (direction > 0 && rightEndActive()) {
    performForcedBackoff(1);
    return;
  }

  unsigned long requestedInterval =
      intervalForCommand(command);

  if (
    controllerState == STATE_MOVING
    && currentDirection == direction
  ) {
    targetIntervalUs = requestedInterval;
    return;
  }

  resetPulseState();
  setPhysicalDirection(direction);

  currentDirection = direction;
  currentIntervalUs = START_INTERVAL_US;
  targetIntervalUs = requestedInterval;
  lastStepChangeUs = micros();

  controllerState = STATE_MOVING;
  enableMotorHardware();
}


void updateAcceleration() {
  if (currentIntervalUs > targetIntervalUs) {
    unsigned long difference =
        currentIntervalUs - targetIntervalUs;

    if (difference <= ACCELERATION_CHANGE_US) {
      currentIntervalUs = targetIntervalUs;
    } else {
      currentIntervalUs -= ACCELERATION_CHANGE_US;
    }

  } else if (currentIntervalUs < targetIntervalUs) {
    unsigned long difference =
        targetIntervalUs - currentIntervalUs;

    unsigned long deceleration =
        ACCELERATION_CHANGE_US * 4;

    if (difference <= deceleration) {
      currentIntervalUs = targetIntervalUs;
    } else {
      currentIntervalUs += deceleration;
    }
  }
}


void generateNormalStepPulse() {
  if (controllerState != STATE_MOVING) {
    return;
  }

  /*
    Poll immediately before every new STEP pulse. This is independent of
    interrupts and prevents serial commands from continuing through an
    already-active physical switch.
  */
  if (currentDirection < 0 && leftEndActive()) {
    emergencyCutMotorFromISR();
    performForcedBackoff(-1);
    return;
  }

  if (currentDirection > 0 && rightEndActive()) {
    emergencyCutMotorFromISR();
    performForcedBackoff(1);
    return;
  }

  unsigned long nowUs = micros();

  if (
    !stepPinHigh
    && nowUs - lastStepChangeUs >= currentIntervalUs
  ) {
    digitalWrite(X_STEP_PIN, HIGH);
    stepPinHigh = true;
    lastStepChangeUs = nowUs;
    return;
  }

  if (
    stepPinHigh
    && nowUs - lastStepChangeUs >= STEP_PULSE_US
  ) {
    digitalWrite(X_STEP_PIN, LOW);
    stepPinHigh = false;
    lastStepChangeUs = nowUs;
    updateAcceleration();
  }
}


void updateNormalHold() {
  if (
    !motorHolding
    || controllerState != STATE_IDLE
  ) {
    return;
  }

  if (millis() - holdStartedMs >= NORMAL_HOLD_MS) {
    digitalWrite(X_EN_PIN, HIGH);
    motorHolding = false;
  }
}


void pollPhysicalEnds() {
  if (
    controllerState == STATE_FAULT
    || backoffInProgress
  ) {
    return;
  }

  if (
    controllerState == STATE_MOVING
    && currentDirection < 0
    && leftEndActive()
  ) {
    emergencyCutMotorFromISR();
    performForcedBackoff(-1);
    return;
  }

  if (
    controllerState == STATE_MOVING
    && currentDirection > 0
    && rightEndActive()
  ) {
    emergencyCutMotorFromISR();
    performForcedBackoff(1);
  }
}


void handleCommand(int command) {
  lastCommandMs = millis();

  if (command == COMMAND_HEARTBEAT) {
    return;
  }

  if (command == COMMAND_IDENTIFY) {
    Serial.println(F("TMC_FAILSAFE_V10"));
    return;
  }

  if (command == COMMAND_CLEAR_FAULT) {
    if (leftEndActive() || rightEndActive()) {
      Serial.println(F("fault not cleared: end stop active"));
      return;
    }

    lockedEnd = 0;
    controllerState = STATE_IDLE;
    disableMotorHardware();

    Serial.println(F("fault cleared: ready"));
    return;
  }

  if (command == COMMAND_EMERGENCY_STOP) {
    lockedEnd = 0;
    enterFault(F("emergency stop latched"));
    return;
  }

  if (command == COMMAND_STOP) {
    if (
      controllerState == STATE_FAULT
      || backoffInProgress
    ) {
      return;
    }

    holdMotor();

    if (lockedEnd != 0) {
      controllerState = STATE_END_LOCKED;
    } else {
      controllerState = STATE_IDLE;
    }

    return;
  }

  if (
    command == -3
    || command == -1
    || command == 1
    || command == 3
  ) {
    startMovement(command);
  }
}


void readSerialCommands() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '\n' || c == '\r') {
      if (serialBuffer.length() > 0) {
        int command = serialBuffer.toInt();
        serialBuffer = "";
        handleCommand(command);
      }
    } else if ((c >= '0' && c <= '9') || c == '-') {
      if (serialBuffer.length() < 12) {
        serialBuffer += c;
      } else {
        serialBuffer = "";
      }
    }
  }
}


void enforceCommunicationWatchdog() {
  if (
    controllerState == STATE_MOVING
    && millis() - lastCommandMs > COMMAND_TIMEOUT_MS
  ) {
    holdMotor();
    controllerState = STATE_IDLE;
  }
}


void setup() {
  Serial.begin(115200);

  pinMode(X_DIR_PIN, OUTPUT);
  pinMode(X_STEP_PIN, OUTPUT);
  pinMode(X_EN_PIN, OUTPUT);

  pinMode(L_END_STOP_PIN, INPUT_PULLUP);
  pinMode(R_END_STOP_PIN, INPUT_PULLUP);

  digitalWrite(X_STEP_PIN, LOW);
  disableMotorHardware();

  /*
    Both switches must be physically released while Arduino starts.
    Their current raw levels become their released baselines.
  */
  delay(50);
  leftReleasedLevel = digitalRead(L_END_STOP_PIN);
  rightReleasedLevel = digitalRead(R_END_STOP_PIN);

  attachInterrupt(
    digitalPinToInterrupt(L_END_STOP_PIN),
    leftEndISR,
    CHANGE
  );

  attachInterrupt(
    digitalPinToInterrupt(R_END_STOP_PIN),
    rightEndISR,
    CHANGE
  );

  lastCommandMs = millis();

  Serial.println(F("TMC_FAILSAFE_V10"));
  Serial.println(F("hard-capped backoff total=100 steps"));
  Serial.println(F("ready 115200"));

  Serial.print(F("left released raw level="));
  Serial.println(leftReleasedLevel);

  Serial.print(F("right released raw level="));
  Serial.println(rightReleasedLevel);

  Serial.print(F("left end initial="));
  Serial.println(leftEndActive() ? F("ACTIVE") : F("released"));

  Serial.print(F("right end initial="));
  Serial.println(rightEndActive() ? F("ACTIVE") : F("released"));
}


void loop() {
  processPendingEndTrip();
  pollPhysicalEnds();
  readSerialCommands();
  processPendingEndTrip();
  pollPhysicalEnds();
  enforceCommunicationWatchdog();
  generateNormalStepPulse();
  updateNormalHold();
}