
# FSE_Capstone_sim- A Compressor Simulator for FS-Elliott
 Grove City College Senior Capstone Project (2025-2026)
 
 **Team members:** Ian Armour, Haddon Baker, James Laird, Kendall Kauffmann, Jacob Schroeder 
 ## IMPORTANT
 This is the second iteration of the Compressor Simulator Project. Previous docs will be preserved but will include different formatting so that the new team's work is distinguishable from the old team's work. 


## Purpose

The FS-Elliott company needed a space-efficient way to test the control panels it produces that control its industrial air compresssors.  They requested a digitally-controlled device that can replicate the electrical signals produced by an air compressor. By attaching the simulator to the control panel, the behavior can be verified without having to connect an actual air compressor.

## Architecture
This repository contains all of the software designed and implemented for both the GUI and Raspberry Pi side. The block diagram below depicts the various flows of signals between input and output, out to the R1000 and in to the Raspberry Pi. Ethernet is still the method of communication used between the Pi and the control laptop. 

<img width="700" alt="gui_populated" src="GUI pics\image.png"/>

## Graphical User Interface
Below is an image of the current state of the graphical user interface, with revisions from last year's simulator. Not only can signals be configured using the default_config.json file, but also by using the dropdowns and other buttons on the user interface. Looking at the old screengrab of the 24/25 GUI gives a good comparison of what has changed since last year. Additionally, there is an error popup and a signal masterkey popup.

- GUI homescreen

<img width="700" alt="gui_populated" src="GUI pics\image-1.png"/>


- Signal Masterkey Popup

<img width="700" alt="gui_populated" src="GUI pics\image-2.png"/>

- Error Popup

<img width="700" alt="gui_populated" src="GUI pics\image-3.png"/>

# --Begin 2024-2025 docs--
 
 ## System Architecture
This project required design of both electrical hardware and software, although this repo contains only the software.  The simulator has two parts: a custom control panel that contains a Raspberry Pi and custom I/O hardware, and a user-operated laptop that controls the simulator.  The two parts communicate over ethernet. Below is a block diagram of the software architecture and behavior:

<img width="700" alt="software_bd" src="https://github.com/user-attachments/assets/401a20b0-1fc5-4ab6-8af1-0207bbacbd21"/>

## User Interface
The engineer can control the simulator using the single-window GUI shown below.  Each of the four types of signals has its own pane, and they can be configured using the `config.json` file.  Analog signals use the 4-20 mA protocol, and digital signals are continuity-based.

<img width="700" alt="gui_populated" src="https://github.com/user-attachments/assets/65e393cf-b7c7-4ce0-bddb-ae959b1b1d96" />

## Custom Control Panel
This panel was custom-made by the Team. The Raspberry Pi is mounted at the top right of the interior.

<img width="300" alt="exterior_labeled" src="https://github.com/user-attachments/assets/753baa34-efbc-4a4e-b453-554c439267a0"/>
<img width="300" alt="exterior_port_side" src="https://github.com/user-attachments/assets/796b5c59-a38a-4a52-b595-a717e1dafdbb"/>
<img width="300" alt="enc_interior" src="https://github.com/user-attachments/assets/7fa434b6-7390-4a43-9a65-47343bfcabef"/>
<!-- END OLD DOCS -->

