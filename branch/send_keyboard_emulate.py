#!/usr/bin/env python3
"""
Эмуляция ввода клавиатуры на Windows: отправляет символьную строку как последовательность нажатий клавиш.

Использование:
python send_keyboard_emulate.py --payload 0456789 --delay 3 --enter

Опции:
--payload  : строка для отправки (по умолчанию "0456789")
--delay    : время в секундах перед отправкой (по умолчанию 3)
--enter    : добавить нажатие Enter в конце

Внимание: этот скрипт эмулирует ввод на хосте — удержите фокус на нужном поле ввода.
"""
import ctypes
import time
import argparse

VK_RETURN = 0x0D

def send_char(ch):
    """Отправляет один символ как клавишу: поддержка цифр и латинских букв."""
    SHIFT = 0x10
    SPECIAL_VK = {
        '@': 0x32,  # Shift+2 on US layout
        '!': 0x31,
        '#': 0x33,
        '$': 0x34,
        '%': 0x35,
        '^': 0x36,
        '&': 0x37,
        '*': 0x38,
        '(': 0x39,
        ')': 0x30,
    }

    if ch in SPECIAL_VK:
        vk = SPECIAL_VK[ch]
        ctypes.windll.user32.keybd_event(SHIFT, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.01)
        ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
        ctypes.windll.user32.keybd_event(SHIFT, 0, 2, 0)
        return

    vk = ord(ch.upper())
    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.01)
    ctypes.windll.user32.keybd_event(vk, 0, 2, 0)

def send_string(s, add_enter=False, inter_delay=0.02):
    for ch in s:
        send_char(ch)
        time.sleep(inter_delay)
    if add_enter:
        ctypes.windll.user32.keybd_event(VK_RETURN, 0, 0, 0)
        time.sleep(0.01)
        ctypes.windll.user32.keybd_event(VK_RETURN, 0, 2, 0)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--payload', type=str, default='qaz@1234qaz@5678')
    parser.add_argument('--delay', type=float, default=3.0)
    parser.add_argument('--enter', action='store_true')
    args = parser.parse_args()

    print(f"Focus the target input now. Sending in {args.delay} seconds: '{args.payload}'")
    try:
        time.sleep(args.delay)
        send_string(args.payload, add_enter=args.enter)
        print('Done')
    except KeyboardInterrupt:
        print('\nAborted by user')

if __name__ == '__main__':
    main()
