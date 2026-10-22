/**
 * @file esp32_camera_firmware.ino
 * @brief ESP32-CAM Smart Study Buddy Firmware
 * 
 * Functions:
 *  - Initializes OV2640 camera sensor with PSRAM allocation.
 *  - Streams JPEG frames over Serial/HTTP.
 *  - Receives real-time focus state (0=Closed, 1=Drowsy, 2=Open, 3=Absent) via UART.
 *  - Drives I2C 16x2 LCD status display, active alarm Buzzer, and Alert LED.
 *  - Monitors physical study session push button with debouncing.
 */

#include <Arduino.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include "esp_camera.h"
#include "board_config.h"
#include "camera_pins.h"

// Instantiate I2C LCD (0x27 address, 16 columns, 2 rows)
LiquidCrystal_I2C lcd(LCD_I2C_ADDR, 16, 2);

// Runtime States
int focusState       = 2;     // Default: 2=Focused/Open
bool sessionStarted  = false; // Session toggle flag
bool lastButtonState = HIGH;  // Pull-up active LOW
unsigned long lastDebounceTime = 0;
const unsigned long debounceDelay = 200;

// Camera configuration struct
camera_config_t cameraConfig;

void initCamera();
void handleSerialCommands();
void checkSessionButton();
void updateActuatorsAndDisplay();

void setup() {
    Serial.begin(SERIAL_BAUD_RATE);
    Serial.setDebugOutput(false);

    // Initialize I2C Bus and LCD
    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
    lcd.init();
    lcd.backlight();
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("SmartStudyBuddy");
    lcd.setCursor(0, 1);
    lcd.print("Initializing...");

    // Initialize Actuator & Sensor GPIOs
    pinMode(RED_LED_PIN, OUTPUT);
    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(START_BTN_PIN, INPUT_PULLUP);

    digitalWrite(RED_LED_PIN, LOW);
    noTone(BUZZER_PIN);

    // Initialize OV2640 Camera
    initCamera();

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Study Buddy Ready");
    lcd.setCursor(0, 1);
    lcd.print("Press Start Btn");
    delay(1000);
}

void loop() {
    handleSerialCommands();
    checkSessionButton();
    updateActuatorsAndDisplay();

    // Capture and transmit frame buffer over Serial
    camera_fb_t* fb = esp_camera_fb_get();
    if (fb) {
        Serial.print("START_IMAGE");
        Serial.write(fb->buf, fb->len);
        Serial.print("END_IMAGE\n");
        esp_camera_fb_return(fb);
    }
}

/**
 * @brief Reads single-byte ocular focus classification from host Python CV pipeline.
 * States:
 *   '0': Eyes Closed (Fatigue alarm)
 *   '1': Half-Blink (Drowsy warning)
 *   '2': Eyes Open (Active focus)
 *   '3': No Face / Away (Distraction alert)
 */
void handleSerialCommands() {
    while (Serial.available()) {
        char c = Serial.read();
        if (c >= '0' && c <= '3') {
            focusState = c - '0';
        }
    }
}

/**
 * @brief Handles debounced push button to toggle active study tracking sessions.
 */
void checkSessionButton() {
    bool currentReading = digitalRead(START_BTN_PIN);

    if (currentReading != lastButtonState && (millis() - lastDebounceTime) > debounceDelay) {
        if (lastButtonState == HIGH && currentReading == LOW) {
            sessionStarted = !sessionStarted;
            lastDebounceTime = millis();

            if (sessionStarted) {
                Serial.print("SESSION_START\n");
                lcd.clear();
                lcd.setCursor(0, 0);
                lcd.print("Session Active");
            } else {
                Serial.print("SESSION_STOP\n");
                lcd.clear();
                lcd.setCursor(0, 0);
                lcd.print("Session Paused");
            }
        }
    }
    lastButtonState = currentReading;
}

/**
 * @brief Actuates Buzzer, Red LED, and updates LCD text based on current focus state.
 */
void updateActuatorsAndDisplay() {
    if (!sessionStarted) {
        digitalWrite(RED_LED_PIN, LOW);
        noTone(BUZZER_PIN);
        return;
    }

    // Trigger audio-visual alert on State 0 (Closed) or State 3 (Absent > 15s)
    if (focusState == 0) {
        // Drowsiness Alert
        digitalWrite(RED_LED_PIN, HIGH);
        tone(BUZZER_PIN, 2000, 100);
        lcd.setCursor(0, 1);
        lcd.print("ALERT: WAKE UP! ");
    } 
    else if (focusState == 3) {
        // Distraction / Absence Alert
        digitalWrite(RED_LED_PIN, HIGH);
        tone(BUZZER_PIN, 1200, 100);
        lcd.setCursor(0, 1);
        lcd.print("AWAY: RETURN!   ");
    } 
    else if (focusState == 1) {
        // Drowsy / Warning
        digitalWrite(RED_LED_PIN, LOW);
        noTone(BUZZER_PIN);
        lcd.setCursor(0, 1);
        lcd.print("Status: Drowsy  ");
    } 
    else {
        // Focused / Eyes Open (State 2)
        digitalWrite(RED_LED_PIN, LOW);
        noTone(BUZZER_PIN);
        lcd.setCursor(0, 1);
        lcd.print("Status: Focused ");
    }
}

/**
 * @brief Configures ESP32-CAM OV2640 registers and initializes sensor driver.
 */
void initCamera() {
    cameraConfig.ledc_channel = LEDC_CHANNEL_0;
    cameraConfig.ledc_timer   = LEDC_TIMER_0;
    cameraConfig.pin_d0       = Y2_GPIO_NUM;
    cameraConfig.pin_d1       = Y3_GPIO_NUM;
    cameraConfig.pin_d2       = Y4_GPIO_NUM;
    cameraConfig.pin_d3       = Y5_GPIO_NUM;
    cameraConfig.pin_d4       = Y6_GPIO_NUM;
    cameraConfig.pin_d5       = Y7_GPIO_NUM;
    cameraConfig.pin_d6       = Y8_GPIO_NUM;
    cameraConfig.pin_d7       = Y9_GPIO_NUM;
    cameraConfig.pin_xclk     = XCLK_GPIO_NUM;
    cameraConfig.pin_pclk     = PCLK_GPIO_NUM;
    cameraConfig.pin_vsync    = VSYNC_GPIO_NUM;
    cameraConfig.pin_href     = HREF_GPIO_NUM;
    cameraConfig.pin_sccb_sda = SIOD_GPIO_NUM;
    cameraConfig.pin_sccb_scl = SIOC_GPIO_NUM;
    cameraConfig.pin_pwdn     = PWDN_GPIO_NUM;
    cameraConfig.pin_reset    = RESET_GPIO_NUM;

    cameraConfig.xclk_freq_hz = 20000000;
    cameraConfig.frame_size   = FRAMESIZE_QVGA;  // 320x240 for high FPS over serial/wifi
    cameraConfig.pixel_format = PIXFORMAT_JPEG;
    cameraConfig.grab_mode    = CAMERA_GRAB_WHEN_EMPTY;
    cameraConfig.fb_location  = CAMERA_FB_IN_PSRAM;
    cameraConfig.jpeg_quality = 12;
    cameraConfig.fb_count     = 1;

    esp_err_t err = esp_camera_init(&cameraConfig);
    if (err != ESP_OK) {
        Serial.printf("[Camera] Init failed with error 0x%x\n", err);
        return;
    }

    sensor_t* s = esp_camera_sensor_get();
    if (s) {
        s->set_hmirror(s, 0);
        s->set_vflip(s, 0);
    }
}
