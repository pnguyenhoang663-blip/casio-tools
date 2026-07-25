; ASM mẫu: Gán giá trị và in hex
org 0xE9E0

start:
    setlr
    setsfr
    di,rt

    ; Gán giá trị
    er0 = hex 12 34 56 78
    er2 = hex 9A BC DE F0

    ; Output hex
    hex 00 11 22 33 44 55 66 77
    hex 88 99 AA BB CC DD EE FF

end:
    goto start