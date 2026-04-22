#define X_EN_PIN  4
#define X_STEP_PIN 5
#define X_DIR_PIN 6

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

attachInterrupt(digitalPinToInterrupt(L_END_STOP_PIN), r_interupt, CHANGE);
attachInterrupt(digitalPinToInterrupt(R_END_STOP_PIN), l_interupt, CHANGE);

}

String ver = "2.0";

void loop() {
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

  digitalWrite(X_STEP_PIN, HIGH);
  delay(2);
  digitalWrite(X_STEP_PIN, LOW);
  delay(1);
}

void r_interupt(){
handle_interupt();
    rightEnd = true;
}

void l_interupt(){
handle_interupt();
    leftEnd = true;
}Ł

void handle_interupt(){
digitalWrite(X_EN_PIN, HIGH);
}
