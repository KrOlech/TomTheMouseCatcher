#define X_EN_PIN  4
#define X_STEP_PIN 6
#define X_DIR_PIN 5

#define L_END_STOP_PIN 2
#define R_END_STOP_PIN 3

//C:\Users\Zenbook\AppData\Local\arduino\sketches\79DA15B7F5DB220941C7F2C9DF39D995

bool rightEnd = false;
bool leftEnd = false;

void setup() {
Serial.begin(9600);

pinMode(X_DIR_PIN, OUTPUT);
pinMode(X_STEP_PIN, OUTPUT);
pinMode(X_EN_PIN, OUTPUT);

digitalWrite(X_EN_PIN, HIGH);

pinMode(L_END_STOP_PIN, INPUT_PULLUP);
pinMode(R_END_STOP_PIN, INPUT_PULLUP);

attachInterrupt(digitalPinToInterrupt(L_END_STOP_PIN), r_interupt, FALLING);
attachInterrupt(digitalPinToInterrupt(R_END_STOP_PIN), l_interupt, FALLING);


digitalWrite(X_DIR_PIN, LOW);
digitalWrite(X_EN_PIN, LOW);
}

String ver = "2.0";

bool in_init = false;

void loop() {

  if (in_init){
  String readString = "";

  while (Serial.available()) {
    delay(3);  //delay to allow buffer to fill
    if (Serial.available() > 0) {
      char c = Serial.read();  //gets one byte from serial buffer
      readString += c; //makes the string readString
    }
  }

  int direction = readString.toInt();

  if (direction == -1 && !leftEnd){
  //left
    digitalWrite(X_DIR_PIN, LOW);
    digitalWrite(X_EN_PIN, LOW);
    Serial.println("left "+ver);
    rightEnd = false;

  }else if(direction == -1 && leftEnd){
    Serial.println("left end "+ver);
  } else if(direction == 1 && !rightEnd){
    //right
      digitalWrite(X_DIR_PIN, HIGH);
      digitalWrite(X_EN_PIN, LOW);
      Serial.println("right "+ver);
      leftEnd = false;

  } else if(direction == 1 && rightEnd){
    Serial.println("right end "+ver);
  } else if (direction == 100){
  //stop
      digitalWrite(X_EN_PIN, HIGH);
      Serial.println("stop "+ver);
  }
    }
  performStep();
}

void r_interupt(){
  digitalWrite(X_DIR_PIN, LOW);
  rightEnd = true;
  Serial.println("R stop "+ver);
  handle_interupt();
}

void l_interupt(){
  digitalWrite(X_DIR_PIN, HIGH);
  leftEnd = true;
    in_init = true;
  Serial.println("L stop "+ver);
  handle_interupt();
}

void handle_interupt(){
  //performTenSteps();
  digitalWrite(X_EN_PIN, HIGH);
}

void performTenSteps(){
  for(int i=0;i<100;i++){
    performStep();
  }
}

void performStep(){
  digitalWrite(X_STEP_PIN, HIGH);
  delay(2);
  digitalWrite(X_STEP_PIN, LOW);
  delay(1);
}
