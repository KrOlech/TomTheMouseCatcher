#include <AccelStepper.h>
#define WRITE_DELAY 20 
#define LOOP_DELAY 20

int reset = 18;
int start = 0;
int step = 2000;
int stop = 300000;// LIMIT NA PRRZESUNIECIE
int deltaT=1000;// CZAS MIEDZY IMPUSLAMI
const byte interruptPinL = 2;// TRIGGER L
const byte interruptPinR = 3;// TRIGGER P
const byte enableL = 8;
const byte stepPinL = 9;
const byte dirPinL = 13;
const byte enableR = 11;
const byte stepPinR = 12;
const byte dirPinR = 10;

int setReset=0;
int positionL = start;
int positionR = start;
unsigned long timeR=0;
unsigned long timeL=0;
volatile byte state = LOW;
int lEnable=0;
int rEnable=0;


void moveR(void);
void moveL(void);
void resetP(void);
void moveStepsNr(int,int,byte,byte);

void setup() {
  Serial.begin(9600);
  Serial.print("Starting NOW\n");

  //pinMode(likometrL, OUTPUT);
  pinMode(enableR, OUTPUT);
  digitalWrite(enableR, HIGH);
  pinMode(enableL, OUTPUT);
  digitalWrite(enableL, HIGH);
  pinMode(stepPinR, OUTPUT);
  pinMode(stepPinL, OUTPUT);
  pinMode(dirPinR, OUTPUT);
  pinMode(dirPinL, OUTPUT);
  //pinMode(LED_BUILTIN, OUTPUT);
  pinMode(interruptPinL, INPUT_PULLUP);
  pinMode(interruptPinR, INPUT_PULLUP);
  pinMode(reset, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(interruptPinL), moveL, FALLING);
  attachInterrupt(digitalPinToInterrupt(interruptPinR), moveR, FALLING);
  attachInterrupt(digitalPinToInterrupt(reset), resetP, FALLING);
  //stepperR.setMaxSpeed(1000);
  //stepperR.setSpeed(1000.);
  //stepperR.setAcceleration(12000);
  //stepperL.setMaxSpeed(1000);
  //stepperL.setSpeed(1000.);
 // stepperL.setAcceleration(12000);
  digitalWrite(enableR, HIGH);
  digitalWrite(enableL, HIGH);
  //digitalWrite(enableR, LOW);     
  //delay(5000);
  //stepper1.setAcceleration(100);  
 
}


void loop() {
  //stepper1.move(1000);
  //stepperR.run();
  if (rEnable==1){
    Serial.print("rEnable==1\n");
    moveStepsNr(step,1,dirPinR,stepPinR);
    rEnable=0;
    digitalWrite(enableR, HIGH);
    delay(50);}

  if (lEnable==1){
    Serial.print("lEnable==1\n");
    moveStepsNr(step,1,dirPinL,stepPinL);
    lEnable=0;
    delay(50);
    digitalWrite(enableL, HIGH);}
  //servoSet(likometrR, 1500-positionR);
  //digitalWrite(LED_BUILTIN, LOW);

  if (setReset==1){
        Serial.print("RESET loop in\n");
  setReset=0;
  digitalWrite(enableR, LOW);
  digitalWrite(enableL, LOW);
  moveStepsNr(positionL,1,dirPinL,stepPinL);
  moveStepsNr(positionR,1,dirPinR,stepPinR);
  positionL=start;
  positionR=start;
  digitalWrite(enableR, HIGH);
  digitalWrite(enableL, HIGH);
  }
}

void moveL() {
    Serial.print("Move L\n");
  int time = millis();
  if((positionL < stop)&&((time-timeL)>deltaT)){
      
      positionL += step;
      Serial.print("posL=");
      Serial.print(positionL);
      Serial.print("\n");
      digitalWrite(enableL, LOW);     
      //stepperL.move(-step);
      //Serial.print("trigL");
      //stepperL.run();
      lEnable=1;
      }
      timeL=time;
      //digitalWrite(LED_BUILTIN, HIGH);
      
}

void moveR() {
      Serial.print("Move R\n");
  int time = millis();
  if((positionR < stop)&&((time-timeR)>deltaT)){
      positionR += step;
      Serial.print("posR=");
      Serial.print(positionR);
      Serial.print("\n");
      rEnable=1;
      digitalWrite(enableR, LOW);   
      //stepperR.move(-step);
      //stepperR.run();
      
      }
      timeR=time;
      //digitalWrite(LED_BUILTIN, HIGH);
   

}


void moveStepsNr(int steps_nr,int direction,byte DIR_PIN, byte STEP_PIN) {
  //digitalWrite(DIR_PIN, LOW);  //LOW to CCW
  //make steps
  int F1;
  int F2;
  if (direction==1)
  {F1=HIGH;
  F2=LOW;}
  else
  {F1=LOW;
  F2=HIGH;}
  for (int i = 0; i <= steps_nr; i++) {
    
    delayMicroseconds(WRITE_DELAY);
    digitalWrite(DIR_PIN, F1);
    delayMicroseconds(500);
    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(WRITE_DELAY);
    digitalWrite(STEP_PIN, LOW);
    digitalWrite(DIR_PIN, F2);
    delayMicroseconds(500);
    delayMicroseconds(LOOP_DELAY);
  }
}

void resetP(){
 // stepperR.moveTo(0);
 //  stepperL.moveTo(0);
    Serial.print("RESET\n");
   setReset=1;}