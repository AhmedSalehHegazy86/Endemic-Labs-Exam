import cv2
import os

def crop_parasite_image(input_path, output_path, crop_box):
    """
    يقوم بقص الصورة بناءً على الإحداثيات المحددة وإزالة أي نصوص أو بيانات جانبية.
    crop_box: (ymin, xmin, ymax, xmax) بالنسبة المئوية أو بالبكسل
    """
    image = cv2.imread(input_path)
    if image is None:
        print(f"Error loading image: {input_path}")
        return
    
    h, w, _ = image.shape
    ymin, xmin, ymax, xmax = crop_box
    
    # حساب الإحداثيات الفعلية للقص
    crop_img = image[int(ymin*h):int(ymax*h), int(xmin*w):int(xmax*w)]
    
    # حفظ الصورة النظيفة (بدون بيانات أو عناوين قديمة)
    cv2.imwrite(output_path, crop_img)
    print(f"Successfully cropped and saved: {output_path}")

# مثال على تشغيل الدالة لصور دورات الحياة والبويضات من الكتاب
# crop_parasite_image("book_page_12.jpg", "app_assets/parasites/schistosoma_ova.jpg", (0.15, 0.10, 0.50, 0.90))
