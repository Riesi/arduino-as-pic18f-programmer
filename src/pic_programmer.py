#!/usr/bin/python

"""
Copyright (C) 2012-2017  Kirill Kulakov, Jose Carlos Granja & Xerxes Ranby

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from serial import *
import getopt
import sys
from Hex import *

mcus = (["18f2455", 0x1260], ["18f2550", 0x1240], ["18f4455", 0x1202], ["18f4550", 0x1200], ["18f2420", 0x1140],
        ["18f2520", 0x1100], ["18f4420", 0x10C0], ["18f4520", 0x1080])


def getOut():
    print "For help use --help"
    sys.exit(2)


def main():
    try:
        options, arguments = getopt.getopt(sys.argv[1:], 'hp:aP:i:le:lv', ['help', 'port=', 'list', 'erase'])
    except getopt.error, msg:
        print msg
        getOut()

    MCU = ""
    PORT = ""
    FILENAME = ""
    ERASE_MODE = False
    verbose = False

    SLEEP_TIME = 0.00001

    for opt, arg in options:
        if opt in ('-h', '--help'):
            helpFile = open("help", "r")
            print helpFile.read() + "\n"
            sys.exit(0)
        elif opt in ('-l', '--list'):
            print "Supported MCUs:"
            for mcu, i in mcus:
                print "pic" + mcu
            sys.exit(0)
        elif opt in ('-e', '--erase'):
            ERASE_MODE = True
        elif opt in ('-p'):
            MCU = arg
        elif opt in ('-P', '--port'):
            PORT = arg
        elif opt in ('-i'):
            FILENAME = arg
        elif opt in ('-v'):
            verbose = True

    if PORT == "":
        PORT = '/dev/ttyACM0'
    if FILENAME == "" and not ERASE_MODE:
        print "You need to select an hex file with -i option"
        getOut()

    print ("Connecting to arduino..."),

    # Open Serial port
    try:
        arduino = Serial(PORT, 38400)
    except SerialException, msg:
        print msg
        sys.exit(2)

    time.sleep(2)

    # Say hello to Arduino
    arduino.write('HX' + '\r\n')
    if arduino.read() == 'H':
        # If Arduino responds, check for the mcu
        print ("\tSuccess")
        print ("Connecting to the mcu..."),
        arduino.flushInput()

        # checking the MCU
        mcu_found = False

        # do not probe for MCU if specified on commandline
        if MCU != "":
            mcu_found = True

        if not mcu_found:
            arduino.write('DX' + '\r\n')  # asking Arduino for the DeviceID
            time.sleep(SLEEP_TIME)
            deviceID = ord(arduino.read()) + ord(arduino.read()) * 256

            for mcu, ID in mcus:
                if ID == deviceID:
                    print "\tYour MCU: " + mcu
                    mcu_found = True

        if mcu_found:
            # Perform Bulk Erase
            print "Erasing chip............",
            arduino.flushInput()
            arduino.write('EX' + '\r\n')
            if arduino.read() == "K":
                print "\tSuccess"

                if not ERASE_MODE:
                    # open and parse the hex file
                    hexFile = Hex(FILENAME)

                    # Program Memory
                    print "Programming flash memory...",
                    if verbose:
                        print "\n",
                    address = 0
                    while address < 0x8000:
                        for i in range(0x20):
                            if hexFile.getData(address + i) != 0xFF:
                                buf = "W"
                                buf += str(hex(address)[2:].zfill(4))
                                for j in range(0x20):
                                    buf += str(hex(hexFile.getData(address + j))[2:].zfill(2))
                                buf += "X"
                                if verbose:
                                    print buf
                                arduino.write(buf.upper())
                                time.sleep(SLEEP_TIME)
                                break
                        address += 0x20
                    print "\tSuccess"

                    # Program IDs
                    print "Programming ID memory...",
                    if verbose:
                        print "\n",
                    # ID 0x200000 - 0x200007
                    address = 0
                    while address < 0x8:
                        for i in range(0x8):
                            if hexFile.getID(address + i) != 0xFF:
                                buf = "W"
                                buf += str(hex(address + 0x200000)[2:].zfill(6))
                                for j in range(0x8):
                                    buf += str(hex(hexFile.getID(address + j))[2:].zfill(2))
                                buf += "X"
                                if verbose:
                                    print buf
                                arduino.write(buf.upper())
                                time.sleep(SLEEP_TIME)
                                break
                        address += 0x8
                    print "\tSuccess"

                    # Program Data EE
                    # TODO only some parts have EEPROM
                    print "Programming EEPROM......",
                    if verbose:
                        print "\n",
                    # EEPROM 0xF00000 - 0xF00100
                    address = 0
                    while address < 0x100:
                        for i in range(0x20):
                            if hexFile.getEEPROM(address + i) != 0xFF:
                                buf = "W"
                                buf += str(hex(address + 0xF00000)[2:].zfill(6))
                                for j in range(0x20):
                                    buf += str(hex(hexFile.getEEPROM(address + j))[2:].zfill(2))
                                buf += "X"
                                if verbose:
                                    print buf
                                arduino.write(buf.upper())
                                time.sleep(SLEEP_TIME)
                                break
                        address += 0x20

                    print "\tSuccess"

                    # verify Program
                    # TODO

                    # verify IDs
                    # TODO

                    # verify Data
                    # TODO

                    # program configuration bits
                    print "Programming the fuse bits...",
                    if verbose:
                        print "\n",
                    for i in range(0x0F):
                        if hexFile.fuseChanged(i):
                            buf = "C" + hex(i)[2:] + hex(hexFile.getFuse(i))[2:].zfill(2) + "X"
                            if verbose:
                                print "fuse "+str(hex(i))+" changed to "+str(hex(hexFile.getFuse(i)))
                                print buf
                            arduino.write(buf.upper())
                            time.sleep(SLEEP_TIME)

                    print "\tSuccess"

                    # verify configuration bits
                    # TODO
            else:
                print "Couldn't erase the chip."
                sys.exit(1)
        else:
            print "MCU not recognized. Check the list of compatible MCU'S and/or check your wire conections."
            sys.exit(1)
    else:
        print "Couldn't connect to the Arduino."
        sys.exit(2)
    arduino.close()


if __name__ == "__main__":
    main()
