#define X_EN_PIN  4//29//3
#define X_STEP_PIN 3//6//4  //B6 or A1
#define X_DIR_PIN 2//7//5   //B5 or A2



/*
Zones:

H1 G1 F1 S1
         E1
A B C D
         E2
H2 G2 F2 S2

0 1 2 3
      3
0 1 2 3
      3
0 1 2 3

*/

int8_t current_zone = 0;

void setup() {
Serial.begin(9600);
pinMode(X_DIR_PIN, OUTPUT);
pinMode(X_STEP_PIN, OUTPUT);
pinMode(X_EN_PIN, OUTPUT);


}

int kad = 0;

void loop() {
  String readString = "";

  while (Serial.available()) {
    delay(3);  //delay to allow buffer to fill
    if (Serial.available() >0) {
      char c = Serial.read();  //gets one byte from serial buffer
      readString += c; //makes the string readString
    }
  }

  int newZone = readString.toInt();
  

  int zoneDelta = current_zone - newZone;

  if (zoneDelta > 0){
        digitalWrite(X_DIR_PIN, LOW);
        digitalWrite(X_EN_PIN, LOW);
        kad = 0;
  }
  else if(zoneDelta < 0){

          digitalWrite(X_DIR_PIN, HIGH);
          digitalWrite(X_EN_PIN, LOW);
          kad = 0;

  } else {
      kad ++;
  }
  if (kad > 400){
      digitalWrite(X_EN_PIN, HIGH);
      kad = 0;
  }

  digitalWrite(X_STEP_PIN, HIGH);
  delay(1);
  digitalWrite(X_STEP_PIN, LOW);
  delay(1);

}