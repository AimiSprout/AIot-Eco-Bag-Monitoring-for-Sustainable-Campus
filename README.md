# AIoT Eco-Bag Monitoring System for Sustainable Campus

## Project Overview

This project is an AIoT-based Eco-Bag Monitoring System designed to automate eco-bag classification, sorting, and monitoring on university campuses. The system integrates Artificial Intelligence, Internet of Things (IoT), cloud database services, and a web dashboard to support sustainability initiatives.

## Features

* Real-time eco-bag classification using MobileNetV2
* Automatic sorting using servo motor
* Firebase Realtime Database integration
* Web-based monitoring dashboard
* Telegram notification for bin-full alerts
* Collection trend prediction using Linear Regression

## Hardware Components

* Raspberry Pi 4 Model B
* Camera Module
* IR Sensor
* Servo Motor
* LCD Display
* PCA9685 Servo Driver

## Software Technologies

* Python
* TensorFlow Lite
* Firebase Realtime Database
* HTML, CSS, JavaScript
* Telegram Bot API
* Scikit-learn

## Project Structure

* main_jadi.py : Main system controller
* prediction.py : Collection prediction module
* eco_bag_model5.tflite : Trained AI classification model
* labels5.txt : Classification labels
* webapp/ : Web dashboard source code
