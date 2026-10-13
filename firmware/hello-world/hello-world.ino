#include <Inkplate.h>

Inkplate display;

void setup() {
    display.begin();
    display.clearDisplay();
    display.setCursor(10, 10);
    display.setTextColor(INKPLATE_BLACK);
    display.setTextSize(6);
    display.print("Hello World!");
    display.display();
}

void loop() {
}
