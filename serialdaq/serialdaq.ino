String cmd = "";
char inByte;
int num_inputs = 1; // Number of analog ins to read
int sample_delay = 5; // Delay between samples in microseconds

int s_start;
int s_end;

void setup() {
  // Open serial port at 115200 bps. Higher baud rates may be possible.
  Serial.begin(115200);
  
  // Uncomment this line for 12-bit DAQ resolution with an Arduino Due board.
  analogReadResolution(12);
}

void loop() {
    if (Serial.available() > 0) {
      delay(300); // wait for the entire command to come through
      cmd = "";
      while (Serial.available() > 0) {
        inByte = Serial.read();
        cmd.concat(inByte);
      }
      if (parseCommand()==0) {
        Serial.print("Received a valid command. Beginning acquisition on ");
        Serial.print(num_inputs);
        Serial.print(" input with a ");
        Serial.print(sample_delay);
        Serial.println(" millisecond delay between sample acquisitions.");
        delay(300);
        acquireData();
      }
    }      
}

int parseCommand() {
  // Commands are submitted with form "CMD I_ D_"
  // where the character following I is the number of 
  // inputs to monitor, and the characters following D 
  // form the intersample delay in milliseconds.
  if (cmd.startsWith("CMD ")) {
    s_start = cmd.indexOf('I', 3)+1;
    s_end = cmd.indexOf(' ', s_start);
    num_inputs = cmd.substring(s_start, s_end).toInt();
    s_start = cmd.indexOf('D', 3)+1;
    s_end = cmd.indexOf(' ', s_start);
    sample_delay = cmd.substring(s_start, s_end).toInt();
    return 0;
  }
  return -1;
}

void acquireData() {
    unsigned long startTime = millis();
    while (Serial.available() == 0) {
      Serial.print("T: ");
      Serial.print(millis()-startTime);
      for (int i=0; i<num_inputs;i++) {
        Serial.print(" : A");
        Serial.print(i);
        Serial.print(": ");
        Serial.print(analogRead(i));
      }
      Serial.println();
      delay(sample_delay);
    }
}    
      
