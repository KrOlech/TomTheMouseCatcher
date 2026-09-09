#define X_EN_PIN  4//29//3
#define X_STEP_PIN 3//6//4  //B6 or A1
#define X_DIR_PIN 2//7//5   //B5 or A2

void setup() {
Serial.begin(9600);

pinMode(X_DIR_PIN, OUTPUT);
pinMode(X_STEP_PIN, OUTPUT);
pinMode(X_EN_PIN, OUTPUT);

digitalWrite(X_EN_PIN, HIGH);


}

String ver = "2.3";

void loop() {

  Serial.println("Engine Driver "+ver);

  String readString = "";

  while (Serial.available()) {
    delay(3);  //delay to allow buffer to fill
    if (Serial.available() > 0) {
      char c = Serial.read();  //gets one byte from serial buffer
      readString += c; //makes the string readString
    }
  }

  int direction = readString.toInt();
  if (direction != 0){
  Serial.print("Steping schoold take ");
  Serial.println(direction*400);

  digitalWrite(X_EN_PIN, LOW);
  
  int x = millis();

  for (int i=0;i<200;i++){
    digitalWrite(X_STEP_PIN, HIGH);
    delay(direction);
    digitalWrite(X_STEP_PIN, LOW);
    delay(direction);
  }

  digitalWrite(X_EN_PIN, HIGH);

  int y = millis();


  Serial.print("Steping took ");
  Serial.println(y-x);

  
  }



}