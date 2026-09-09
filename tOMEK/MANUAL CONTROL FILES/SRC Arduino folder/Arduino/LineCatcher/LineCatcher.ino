#define X_EN_PIN 4
#define X_STEP_PIN 6
#define X_DIR_PIN 5

#define L_END_STOP_PIN 2
#define R_END_STOP_PIN 3

#define LEFT_DIRECTION LOW
#define RIGHT_DIRECTION HIGH
d
// Starts slowly, then accelerates to the previous maximum speed.
const unsigned long START_STEP_INTERVAL_US = 15000;
const unsigned long MAX_SPEED_STEP_INTERVAL_US = 3000;
const unsigned long STEP_PULSE_US = 20;
const unsigned long ACCELERATION_CHANGE_US = 400;

const unsigned long COMMAND_TIMEOUT_MS = 600;

const int COMMAND_HEARTBEAT = 0;
const int COMMAND_LEFT = -1;
const int COMMAND_RIGHT = 1;
const int COMMAND_STOP = 100;

int currentDirection = COMMAND_STOP;
bool stepPinHigh = false;
unsigned long lastStepChangeUs = 0;
unsigned long lastCommandMs = 0;
unsigned long currentStepIntervalUs = START_STEP_INTERVAL_US;

String serialBuffer = "";

bool leftEndActive() {
  return digitalRead(L_END_STOP_PIN) == LOW;
}

bool rightEndActive() {
  return digitalRead(R_END_STOP_PIN) == LOW;
}

void disableMotor() {
  currentDirection = COMMAND_STOP;
  digitalWrite(X_STEP_PIN, LOW);
  stepPinHigh = false;
  digitalWrite(X_EN_PIN, HIGH);
  currentStepIntervalUs = START_STEP_INTERVAL_US;
}

void startMoving(int direction) {
  if (direction == COMMAND_LEFT && leftEndActive()) {
    disableMotor();
    Serial.println("left end");
    return;
  }

  if (direction == COMMAND_RIGHT && rightEndActive()) {
    disableMotor();
    Serial.println("right end");
    return;
  }

  // Repeated command in the same direction only refreshes the watchdog.
  // It must not restart acceleration and must not print repeatedly.
  if (currentDirection == direction) {
    return;
  }

  // Every start or reversal begins slowly and then accelerates.
  digitalWrite(X_STEP_PIN, LOW);
  stepPinHigh = false;
  currentStepIntervalUs = START_STEP_INTERVAL_US;
  lastStepChangeUs = micros();

  if (direction == COMMAND_LEFT) {
    digitalWrite(X_DIR_PIN, LEFT_DIRECTION);
    currentDirection = COMMAND_LEFT;
    Serial.println("left");
  } else {
    digitalWrite(X_DIR_PIN, RIGHT_DIRECTION);
    currentDirection = COMMAND_RIGHT;
    Serial.println("right");
  }

  digitalWrite(X_EN_PIN, LOW);
}

void handleCommand(int command) {
  lastCommandMs = millis();

  if (command == COMMAND_HEARTBEAT) {
    return;
  }

  if (command == COMMAND_LEFT || command == COMMAND_RIGHT) {
    startMoving(command);
  } else if (command == COMMAND_STOP) {
    if (currentDirection != COMMAND_STOP) {
      disableMotor();
      Serial.println("stop");
    }
  }
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '\n' || c == '\r') {
      if (serialBuffer.length() > 0) {
        handleCommand(serialBuffer.toInt());
        serialBuffer = "";
      }
    } else if ((c >= '0' && c <= '9') || c == '-') {
      serialBuffer += c;
    }
  }
}

void enforceEndStops() {
  if (currentDirection == COMMAND_LEFT && leftEndActive()) {
    disableMotor();
    Serial.println("left end");
  } else if (currentDirection == COMMAND_RIGHT && rightEndActive()) {
    disableMotor();
    Serial.println("right end");
  }
}

void enforceCommunicationWatchdog() {
  if (currentDirection != COMMAND_STOP &&
      millis() - lastCommandMs > COMMAND_TIMEOUT_MS) {
    disableMotor();
    Serial.println("watchdog stop");
  }
}

void accelerateAfterStep() {
  if (currentStepIntervalUs > MAX_SPEED_STEP_INTERVAL_US) {
    unsigned long nextInterval = currentStepIntervalUs - ACCELERATION_CHANGE_US;
    currentStepIntervalUs =
        (nextInterval < MAX_SPEED_STEP_INTERVAL_US)
            ? MAX_SPEED_STEP_INTERVAL_US
            : nextInterval;
  }
}

void generateStepPulse() {
  if (currentDirection == COMMAND_STOP) {
    return;
  }

  unsigned long nowUs = micros();

  if (!stepPinHigh && nowUs - lastStepChangeUs >= currentStepIntervalUs) {
    digitalWrite(X_STEP_PIN, HIGH);
    stepPinHigh = true;
    lastStepChangeUs = nowUs;
  } else if (stepPinHigh && nowUs - lastStepChangeUs >= STEP_PULSE_US) {
    digitalWrite(X_STEP_PIN, LOW);
    stepPinHigh = false;
    lastStepChangeUs = nowUs;
    accelerateAfterStep();
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
  disableMotor();
  lastCommandMs = millis();
  Serial.println("ready");
}

void loop() {
  readSerialCommands();
  enforceEndStops();
  enforceCommunicationWatchdog();
  generateStepPulse();
}