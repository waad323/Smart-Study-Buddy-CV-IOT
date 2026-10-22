/**
 * @file camera_pins.h
 * @brief Standard AI-Thinker ESP32-CAM OV2640 Pinout Configuration
 */

#ifndef CAMERA_PINS_H
#define CAMERA_PINS_H

// Camera Data Pins
#define Y2_GPIO_NUM     5
#define Y3_GPIO_NUM     18
#define Y4_GPIO_NUM     19
#define Y5_GPIO_NUM     21
#define Y6_GPIO_NUM     36
#define Y7_GPIO_NUM     39
#define Y8_GPIO_NUM     34
#define Y9_GPIO_NUM     35

// Camera Timing & Control Pins
#define XCLK_GPIO_NUM   0
#define PCLK_GPIO_NUM   22
#define VSYNC_GPIO_NUM  25
#define HREF_GPIO_NUM   23
#define SIOD_GPIO_NUM   26
#define SIOC_GPIO_NUM   27

#define PWDN_GPIO_NUM   32
#define RESET_GPIO_NUM  -1

#endif // CAMERA_PINS_H
