import os
import time
import urllib.parse
import requests
from playwright.sync_api import sync_playwright
import google.generativeai as genai

# جلب المفاتيح السرية من إعدادات GitHub بأمان
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# الكلمات المفتاحية التي سيبحث عنها يومياً في الجزائر (يمكنك تعديلها أو زيادتها)
KEYWORDS = [
    "التوصيل لباب المنزل",
    "الدفع عند الاستلام",
    "ديكور منزلي",
    "Livraison 58 wilayas"
]

def scrape_ads_for_keywords(keywords, country="DZ"):
    """فتح مكتبة فيسبوك وسحب الإعلانات لكل الكلمات المفتاحية"""
    combined_text = ""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for kw in keywords:
            encoded_kw = urllib.parse.quote(kw)
            url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={country}&q={encoded_kw}&media_type=all"
            try:
                page.goto(url, timeout=60000)
                time.sleep(5)
                # التمرير لأسفل لتحميل إعلانات أكثر
                page.mouse.wheel(0, 4000)
                time.sleep(3)
                
                text = page.inner_text("body")
                combined_text += f"\n--- نتائج البحث عن: {kw} ---\n" + text[:6000]
            except Exception as e:
                print(f"خطأ في كلمة {kw}: {e}")
                
        browser.close()
    return combined_text

def send_telegram_report(text):
    """إرسال التقرير النهائي إلى حسابك في تيليجرام"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    # تقسيم الرسالة إذا كانت طويلة جداً
    for i in range(0, len(text), 4000):
        payload = {
            "chat_id": CHAT_ID,
            "text": text[i:i+4000]
        }
        requests.post(url, json=payload)

def main():
    print("بدء فحص الإعلانات اليومي...")
    raw_data = scrape_ads_for_keywords(KEYWORDS)
    
    prompt = f"""
    أنت خبير تجارة إلكترونية (Ad Spy) في السوق الجزائري.
    هذه بيانات حية مسحوبة الآن من مكتبة إعلانات فيسبوك:
    {raw_data}
    
    استخرج لي منها "تقرير المساء لأفضل المنتجات الرابحة اليوم" (اختر أفضل 4 إلى 6 منتجات حقيقية وتجنب الإعلانات غير التجارية).
    لكل منتج اذكر:
    1. 📦 اسم المنتج وفكرته.
    2. 🏪 اسم الصفحة المعلنة.
    3. 💰 السعر وتفاصيل العرض (إن وجد في النص).
    4. 📅 متى بدأ الإعلان ولماذا تراه منتجاً ناجحاً؟
    
    اجعل التقرير منسقاً وواضحاً وجاهزاً للقراءة في تيليجرام.
    """
    
    response = model.generate_content(prompt)
    send_telegram_report(f"🕵️‍♂️ تقرير التجسس اليومي للمنتجات الرابحة:\n\n{response.text}")
    print("تم إرسال التقرير بنجاح!")

if __name__ == "__main__":
    main()
