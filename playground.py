import cv2

lenna = cv2.imread('./assets/host-lenna.bmp',0)
lenna_drive = cv2.imread('./assets/lenna_drive.bmp',0)

print((lenna==lenna_drive).all())

man = cv2.imread('./assets/host-man.bmp',0)
man_drive = cv2.imread('./assets/man_drive.bmp',0)

print((man==man_drive).all())

watermark = cv2.imread('./assets/watermark-snykk.png',0)
watermark_drive = cv2.imread('./assets/watermark_drive.bmp',0)

print((watermark==watermark_drive).all())