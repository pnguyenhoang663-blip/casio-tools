; ASM mẫu: Hello World
org 0xE9E0

start:
    setlr
    setsfr
    di,rt
    buffer_clear
    render.ddd4

    ; In dòng chữ
    xr0 = hex 01 01, adr(text)
    line_print
    render.ddd4

    goto start

lbl text
    "Hello World"
    hex 00