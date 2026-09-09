#define X_EN_PIN 4
#define X_STEP_PIN 6
#define X_DIR_PIN 5

#define L_END_STOP_PIN 2
#define R_END_STOP_PIN 3

// Keep the same direction convention as the original sketch.
#define LEFT_DIRECTION LOW
#define RIGHT_DIRECTION HIGH

const unsigned long STEP_INTERVAL_US = 2000;   // about 333 steps/s
const unsigned long STEP_PULSE_US = 20;
const unsigned long COMMAND_TIMEOUT_MS = 350;  // fail-safe watchdog

const int COMMAND_LEFT = -1;
const int COMMAND_RIGHT = 1;
const int COMMAND_STOP = 100;

int currentDirection = COMMAND_STOP;
bool stepPinHigh = false;
unsigned long lastStepChangeUs = 0;
unsigned long lastCommandMs = 0;

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
}

void startMoving(int direction) {
  if (direction == COMMAND_LEFT) {
    if (leftEndActive()) {
      disableMotor();
      Serial.println("left end 3.0");
      return;
    }
    digitalWrite(X_DIR_PIN, LEFT_DIRECTION);
    currentDirection = COMMAND_LEFT;
    digitalWrite(X_EN_PIN, LOW);
    Serial.println("left 3.0");
  }
  else if (direction == COMMAND_RIGHT) {
    if (rightEndActive()) {
      disableMotor();
      Serial.println("right end 3.0");
      return;
    }
    digitalWrite(X_DIR_PIN, RIGHT_DIRECTION);
    currentDirection = COMMAND_RIGHT;
    digitalWrite(X_EN_PIN, LOW);
    Serial.println("right 3.0");
  }
}

void handleCommand(int command) {
  lastCommandMs = millis();

  if (command == COMMAND_LEFT || command == COMMAND_RIGHT) {
    startMoving(command);
  }
  else if (command == COMMAND_STOP) {
    disableMotor();
    Serial.println("stop 3.0");
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
    }
    else if ((c >= '0' && c <= '9') || c == '-') {
      serialBuffer += c;
    }
  }
}

void enforceEndStops() {
  if (currentDirection == COMMAND_LEFT && leftEndActive()) {
    disableMotor();
    Serial.println("left end 3.0");
  }
  else if (currentDirection == COMMAND_RIGHT && rightEndActive()) {
    disableMotor();
    Serial.println("right end 3.0");
  }
}

void enforceCommunicationWatchdog() {
  if (currentDirection != COMMAND_STOP &&
      millis() - lastCommandMs > COMMAND_TIMEOUT_MS) {
    disableMotor();
    Serial.println("watchdog stop 3.0");
  }
}

void generateStepPulse() {
  if (currentDirection == COMMAND_STOP) {
    return;
  }

  unsigned long nowUs = micros();

  if (!stepPinHigh && nowUs - lastStepChangeUs >= STEP_INTERVAL_US) {
    digitalWrite(X_STEP_PIN, HIGH);
    stepPinHigh = true;
    lastStepChangeUs = nowUs;
  }
  else if (stepPinHigh && nowUs - lastStepChangeUs >= STEP_PULSE_US) {
    digitalWrite(X_STEP_PIN, LOW);
    stepPinHigh = false;
    lastStepChangeUs = nowUs;
  }
}

void setup() {
  Serial.begin(9600);

  pinMode(X_DIR_PIN, OUTPUT);
  pinMode(X_STEP_PIN, OUTPUT);
  pinMode(X_EN_PIN, OUTPUT);

  pinMode(L_END_STOP_PIN, INPUT_PULLUP);
  pinMode(R_END_STOP_PIN, INPUT_PULLUP);

  digitalWrite(X_STEP_PIN, LOW);
  disableMotor();

  lastCommandMs = millis();
  Serial.println("ready 3.0");
}

void loop() {
  readSerialCommands();
  enforceEndStops();
  enforceCommunicationWatchdog();
  generateStepPulse();
}
