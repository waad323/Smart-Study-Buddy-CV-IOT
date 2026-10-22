/**
 * @file board_config.h
 * @brief Peripheral Pin Mappings and Hardware Constants for Study Buddy
 */

#ifndef BOARD_CONFIG_H
#define BOARD_CONFIG_H

// Actuator and Sensor GPIO Mappings
#define RED_LED_PIN     40    // Visual fatigue warning LED
#define BUZZER_PIN      41    // Piezoelectric audio buzzer alarm
#define START_BTN_PIN   19    // Physical session toggle push button (Active LOW)

// I2C Pins for 16x2 LCD Display (PCF8574 Backpack)
#define I2C_SDA_PIN     1
#define I2C_SCL_PIN     2
#define LCD_I2C_ADDR    0x27

// UART Serial Communication
#define SERIAL_BAUD_RATE 115200

#endif // BOARD_CONFIG_H
