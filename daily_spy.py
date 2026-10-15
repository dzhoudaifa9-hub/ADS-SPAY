import os
import time
import urllib.parse
import requests
from playwright.sync_api import sync_playwright
import google.generativeai as genai

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

KEYWORDS = [
    "التوصيل لباب المنزل",
    "الدفع عند الاستلام",
    "ديكور منزلي",
    "Livraison 58 wilayas"
]

def scrape_ads_with_links(keywords, country="DZ"):
    """سحب نصوص الإعلانات مع استخراج الروابط وأرقام الإعلانات"""
    combined_data = ""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for kw in keywords:
            encoded_kw = urllib.parse.quote(kw)
            url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={country}&q={encoded_kw}&media_type=all"
            try:
                page.goto(url, timeout=60000)
                time.sleep(5)
                page.mouse.wheel(0, 4000)
                time.sleep(3)
                
                # استخراج النص مع جميع الروابط (صفحات الهبوط وصفحات فيسبوك) عبر JavaScript
                extracted = page.evaluate("""() => {
                    let text = document.body.innerText;
                    let links = Array.from(document.querySelectorAll('a'))
                        .map(a => a.href)
                        .filter(href => href && !href.includes('facebook.com/ads/library') && !href.includes('help'));
                    let uniqueLinks = [...new Set(links)].slice(0, 40);
                    return text.substring(0, 7000) + "\\n\\n--- الروابط المستخرجة من الصفحة ---\\n" + uniqueLinks.join("\\n");
                }""")
                
                combined_data += f"\n=== نتائج البحث عن: {kw} ===\n" + extracted
            except Exception as e:
                print(f"خطأ في كلمة {kw}: {e}")
                
        browser.close()
    return combined_data

def send_telegram_report(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    for i in range(0, len(text), 4000):
        payload = {
            "chat_id": CHAT_ID,
            "text": text[i:i+4000],
            "disable_web_page_preview": False
        }
        requests.post(url, json=payload)

def main():
    print("بدء الفحص المتقدم مع الروابط...")
    raw_data = scrape_ads_with_links(KEYWORDS)
    
    prompt = f"""
    أنت خبير تجارة إلكترونية (Ad Spy) في السوق الجزائري.
    هذه بيانات حية مسحوبة من مكتبة إعلانات فيسبوك مع الروابط الموجودة فيها:
    {raw_data}
    
    استخرج لي "تقرير أفضل المنتجات الرابحة اليوم" (اختر 4 إلى 6 منتجات).
    لكل منتج اذكر بوضوح:
    1. 📦 اسم المنتج وفكرته وتفاصيل السعر/العرض.
    2. 🏪 اسم الصفحة المعلنة (مع وضع رابطها إن وجد).
    3. 🔗 رابط مشاهدة الإعلان والصور مباشرة: ابحث عن رقم تعريف الإعلان (Library ID أو معرف المكتبة) الموجود بجانب كل إعلان، وركّبه في هذا الرابط المباشر لكي أضغط عليه وأرى الصور والفيديو:
       https://www.facebook.com/ads/library/?id=PUT_ID_HERE
       (استبدل PUT_ID_HERE بالرقم الحقيقي للإعلان).
    4. 🌐 رابط صفحة الهبوط (المتجر الإلكتروني): استخرجه من قائمة الروابط المرفقة (غالباً تكون روابط متاجر خارجية أو روابط l.facebook.com).
    5. 📈 تاريخ بدء الإعلان وتقييمك لسبب نجاحه.
    """
    
    response = model.generate_content(prompt)
    send_telegram_report(f"🕵️‍♂️ تقرير التجسس اليومي (مدعم بالروابط المباشرة):\n\n{response.text}")
    print("تم إرسال التقرير بنجاح!")

if __name__ == "__main__":
    main()
