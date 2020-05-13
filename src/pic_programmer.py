#!/usr/bin/python

"""
Copyright (C) 2012-2020  Kirill Kulakov, Jose Carlos Granja, Xerxes Ranby & Stefan Riesenberger

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
import sys
import getopt
from serial import *
from Hex import Hex

mcus = (["18f2455", 0x1260], ["18f2550", 0x1240], ["18f4455", 0x1202],
        ["18f4550", 0x1200], ["18f2420", 0x1140], ["18f2520", 0x1100],
        ["18f4420", 0x10C0], ["18f4520", 0x1080])


def getOut():
    print("For help use --help")
    sys.exit(2)


def main():
    try:
        options, arguments = getopt.getopt(sys.argv[1:],
                                           'hp:aP:i:levV', ['help', 'port=', 'list', 'erase'])
    except getopt.GetoptError as msg:
        print(msg)
        getOut()

    MCU = ""
    PORT = ""
    FILENAME = ""
    ERASE_MODE = False
    verbose = False
    extraVerbose = False

    for opt, arg in options:
        if opt in ('-h', '--help'):
            helpFile = open("help", "r")
            print(helpFile.read() + "\n")
            sys.exit(0)
        elif opt in ('-l', '--list'):
            print("Supported MCUs:")
            for mcu, i in mcus:
                print("pic" + mcu)
            sys.exit(0)
        elif opt in ('-e', '--erase'):
            ERASE_MODE = True
        elif opt in ('-p'):
            MCU = arg
        elif opt in ('-P', '--port'):
            PORT = arg
        elif opt in ('-i'):
            FILENAME = arg
        elif opt in ('-V'):
            extraVerbose = True
            verbose = True
        elif opt in ('-v'):
            verbose = True

    if PORT == "":
        PORT = '/dev/ttyACM0'
    if FILENAME == "" and not ERASE_MODE:
        print("You need to select an hex file with -i option")
        getOut()

    print("Connecting to arduino...", end = '')

    # Open Serial port
    try:
        arduino = Serial(PORT, 2000000)
    except(SerialException, msg):
        print(msg)
        sys.exit(2)

    time.sleep(2)

    # Say hello to Arduino
    arduino.flushInput()
    arduino.write('HX'.encode('utf-8'))
    if arduino.read().decode('utf-8') == 'H':
        # If Arduino responds, check for the mcu
        print("\tSuccess")
        print("Connecting to the mcu...", end = '')

        # checking the MCU
        mcu_found = False

        # do not probe for MCU if specified on commandline
        if MCU != "":
            mcu_found = True

        if not mcu_found:
            arduino.flushInput()
            arduino.write('DX'.encode('utf-8'))  # asking Arduino for the DeviceID
            deviceID = ord(arduino.read().decode('utf-8')) + ord(arduino.read().decode('utf-8')) * 256

            for mcu, ID in mcus:
                if ID == deviceID:
                    print("\tYour MCU: " + mcu)
                    mcu_found = True

        if mcu_found:
            # Perform Bulk Erase
            print("Erasing chip............", end = '')
            arduino.flushInput()
            arduino.write('EX'.encode('utf-8'))
            if arduino.read().decode('utf-8') == "K":
                print("\tSuccess")

                if not ERASE_MODE:
                    # open and parse the hex file
                    hexFile = Hex(FILENAME)

                    # Program Memory
                    print("Programming flash memory...", end = '')
                    if verbose:
                        print("\n")
                    address = 0
                    while address < 0x8000:
                        if hexFile.haveData(address):
                            buf = "W"
                            buf += str(hex(address)[2:].zfill(4))
                            for j in range(0x20):
                                buf += str(hex(hexFile.getData(address + j))[2:].zfill(2))
                            buf += "X"
                            if verbose:
                                print(buf)
                            arduino.flushInput()
                            arduino.write(buf.upper().encode('utf-8'))
                            arduino.read()
                        address += 0x20
                    print("\tSuccess")

                    # Program IDs
                    if hexFile.haveID():
                        print("Programming ID memory...", end = '')
                        if verbose:
                            print("\n")
                        # ID 0x200000 - 0x200007
                        address = 0

                        buf = "W"
                        buf += str(hex(address + 0x200000)[2:].zfill(6))
                        for j in range(0x8):
                            buf += str(hex(hexFile.getID(address + j))[2:].zfill(2))
                        buf += "X"
                        if verbose:
                            print(buf)
                        arduino.flushInput()
                        arduino.write(buf.upper().encode('utf-8'))
                        arduino.read()
                        print("\tSuccess")

                    # Program Data EE
                    # TODO only some parts have EEPROM
                    print("Programming EEPROM......", end = '')
                    if verbose:
                        print("\n")
                    # EEPROM 0xF00000 - 0xF00100
                    address = 0
                    while address < 0x100:
                        if hexFile.haveEEPROM(address):
                            buf = "W"
                            buf += str(hex(address + 0xF00000)[2:].zfill(6))
                            for j in range(0x20):
                                buf += str(hex(hexFile.getEEPROM(address + j))[2:].zfill(2))
                            buf += "X"
                            if verbose:
                                print(buf)
                            arduino.flushInput()
                            arduino.write(buf.upper().encode('utf-8'))
                            arduino.read()
                        address += 0x20

                    print("\tSuccess")

                    # verify Program
                    print("Verify flash memory.....", end = '')
                    verification = 1
                    if verbose:
                        print("\n")
                    address = 0
                    while address < 0x8000:
                        if hexFile.haveData(address):

                            # Send read command
                            buf = "R"
                            buf += str(hex(address)[2:].zfill(6))
                            buf += "X"
                            arduino.flushInput()
                            arduino.write((buf).upper().encode('utf-8'))
                            arduino.read()

                            # Receive data
                            buf = ""
                            r = arduino.read().decode('utf-8')
                            while r != "X":
                                buf += r
                                r = arduino.read().decode('utf-8')
                            buf += r

                            if verbose:
                                print(buf)

                            # Compare
                            c, buf = buf[:1], buf[1:]
                            if c != "R":
                                print("abort; wrong command received from arduino")
                                return 1

                            iAddress, buf = int(buf[:6], 16), buf[6:]
                            for j in range(0x20):
                                data, buf = int(buf[:2], 16), buf[2:]
                                compare_data = hexFile.getData(iAddress + j)
                                if compare_data != data:
                                    print("verification failed "+
                                          str(hex(compare_data))[2:].zfill(2)+
                                          " do not match "+str(hex(data))[2:].zfill(2))
                                    verification = 0

                        address += 0x20
                    if verification == 0:
                        print("\tFailed")
                    else:
                        print("\tSuccess")

                    # verify IDs
                    print("Verify ID memory........", end = '')
                    verification = 1
                    if verbose:
                        print("\n")
                    if hexFile.haveID():
                        # Send read command
                        buf = "R"
                        buf += str(hex(0x200000)[2:].zfill(6))
                        buf += "X"
                        arduino.flushInput()
                        arduino.write((buf).upper().encode('utf-8'))
                        arduino.read()

                        # Receive data
                        buf = ""
                        r = arduino.read().decode('utf-8')
                        while r != "X":
                            buf += r
                            r = arduino.read().decode('utf-8')
                        buf += r

                        if verbose:
                            print(buf)

                        # Compare
                        c = buf[:1]
                        if c == "K":
                            #workaround python serial bug... K received twice!
                            # remove R
                            buf = buf[1:]
                            c = buf[:1]
                        if c != "R":
                            print("abort; wrong command received from arduino")
                            return 1
                        # remove R
                        buf = buf[1:]

                        iAddress, buf = int(buf[:6], 16), buf[6:]
                        for j in range(0x8):
                            data, buf = int(buf[:2], 16), buf[2:]
                            compare_data = hexFile.getID(iAddress - 0x200000 + j)
                            if compare_data != data:
                                print("verification failed "+
                                      str(hex(compare_data))[2:].zfill(2)+
                                      " do not match "+str(hex(data))[2:].zfill(2))
                                verification = 0
                    if verification == 0:
                        print("\tFailed")
                    else:
                        print("\tSuccess")

                    # verify EEPROM Data
                    print("Verify EEPROM memory....", end = '')
                    verification = 1
                    if verbose:
                        print("\n")
                    address = 0
                    while address < 0x100:
                        if hexFile.haveEEPROM(address):

                            # Send read command
                            buf = "R"
                            buf += str(hex(address + 0xF00000)[2:].zfill(6))
                            buf += "X"
                            arduino.flushInput()
                            arduino.write((buf).upper().encode('utf-8'))
                            arduino.read()

                            # Receive data
                            buf = ""
                            r = arduino.read().decode('utf-8')
                            while r != "X":
                                buf += r
                                r = arduino.read().decode('utf-8')
                            buf += r

                            if verbose:
                                print(buf)

                            # Compare
                            c = buf[:1]
                            if c == "K":
                                #workaround python serial bug... K received twice!
                                # remove R
                                buf = buf[1:]
                                c = buf[:1]
                            if c != "R":
                                print("abort; wrong command received from arduino")
                                return 1
                            # remove R
                            buf = buf[1:]

                            iAddress, buf = int(buf[:6], 16), buf[6:]
                            for j in range(0x20):
                                data, buf = int(buf[:2], 16), buf[2:]
                                compare_data = hexFile.getEEPROM(iAddress - 0xF00000 + j)
                                if compare_data != data:
                                    print("verification failed "+
                                          str(hex(compare_data))[2:].zfill(2)+
                                          " do not match "+str(hex(data))[2:].zfill(2))
                                    verification = 0

                        address += 0x20
                    if verification == 0:
                        print("\tFailed")
                    else:
                        print("\tSuccess")

                    # program configuration bits
                    print("Programming the fuse bits...", end = '')
                    if verbose:
                        print("\n")
                    for i in range(0x0F):
                        if hexFile.fuseChanged(i):
                            buf = "C" + hex(i)[2:] + hex(hexFile.getFuse(i))[2:].zfill(2) + "X"
                            if verbose:
                                if extraVerbose:
                                    print("fuse "+str(hex(i))+
                                          " changed to "+str(hex(hexFile.getFuse(i))))
                                print(buf)
                            arduino.flushInput()
                            arduino.write(buf.upper().encode('utf-8'))
                            arduino.read()

                    print("\tSuccess")

                    # verify configuration bits
                    # TODO
            else:
                print("Couldn't erase the chip.")
                sys.exit(1)
        else:
            print("MCU not recognized. Check the list of compatible MCU'S \
                and/or check your wire conections.")
            sys.exit(1)
    else:
        print("Couldn't connect to the Arduino.")
        sys.exit(2)
    arduino.close()


if __name__ == "__main__":
    main()
