def detect_value(frame, category):
    # サンプル上のバグ: フレーム10では 15 を返してしまう
    if frame == 10:
        return 15
    return frame


