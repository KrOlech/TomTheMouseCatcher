#define X_EN_PIN  4//29//3
#define X_STEP_PIN 3//6//4  //B6 or A1
#define X_DIR_PIN 2//7//5   //B5 or A2

void setup() {
Serial.begin(9600);

pinMode(X_DIR_PIN, OUTPUT);
pinMode(X_STEP_PIN, OUTPUT);
pinMode(X_EN_PIN, OUTPUT);

analogWrite(X_STEP_PIN,127); //500 hz
}

String ver = "1.2";

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

  if (direction == -1 ){
  //left
    digitalWrite(X_DIR_PIN, LOW);
    digitalWrite(X_EN_PIN, LOW);
    Serial.println("left "+ver);ś
  }
  else if(direction == 1){
  //right
      digitalWrite(X_DIR_PIN, HIGH);
      digitalWrite(X_EN_PIN, LOW);
      Serial.println("right "+ver);

  } else if (direction == 100){
  //stop
      digitalWrite(X_EN_PIN, HIGH);
      Serial.println("stop "+ver);
  }
}