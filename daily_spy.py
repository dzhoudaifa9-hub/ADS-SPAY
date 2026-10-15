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

# الكلمات المفتاحية (يمكنك تعديلها أو إضافة مجالات تهمك)
KEYWORDS = [
    "التوصيل لباب المنزل",
    "الدفع عند الاستلام",
    "ديكور منزلي",
    "Livraison 58 wilayas"
]

def scrape_ads_with_links(keywords, country="DZ"):
    """سحب الإعلانات مع فك تشفير روابط المتاجر وأرقام الإعلانات بدقة"""
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
                # التمرير لأسفل لتحميل مجموعة جيدة من الإعلانات
                for _ in range(3):
                    page.mouse.wheel(0, 3000)
                    time.sleep(2)
                
                # استخراج كل إعلان مع الروابط الخاصة به وفك روابط فيسبوك المباشرة
                extracted = page.evaluate("""() => {
                    let results = [];
                    let blocks = Array.from(document.querySelectorAll('div')).filter(
                        el => (el.innerText.includes('Library ID:') || el.innerText.includes('معرف المكتبة:')) 
                        && el.innerText.length > 100 && el.innerText.length < 2500
                    );
                    
                    let seenIds = new Set();
                    for (let b of blocks) {
                        let text = b.innerText;
                        let idMatch = text.match(/(?:Library ID|معرف المكتبة|ID de la bibliothèque)\\s*:\\s*(\\d+)/i);
                        let adId = idMatch ? idMatch[1] : null;
                        
                        if (adId && !seenIds.has(adId)) {
                            seenIds.add(adId);
                            let links = Array.from(b.querySelectorAll('a')).map(a => {
                                try {
                                    let u = new URL(a.href);
                                    // فك رابط التوجيه الخاص بفيسبوك لاستخراج رابط المتجر الأصلي مباشرة
                                    if (u.hostname.includes('l.facebook.com') && u.searchParams.get('u')) {
                                        return decodeURIComponent(u.searchParams.get('u'));
                                    }
                                    return a.href;
                                } catch(e) { return a.href; }
                            }).filter(h => h && !h.includes('ads/library') && !h.includes('/help/'));
                            
                            let uniqueLinks = [...new Set(links)];
                            results.push(`📌 [رقم الإعلان ID: ${adId}]\nالنص:\n${text}\nالروابط المرفقة بهذا الإعلان:\n${uniqueLinks.join('\\n')}`);
                        }
                        if (results.length >= 12) break;
                    }
                    
                    if (results.length === 0) {
                        return document.body.innerText.substring(0, 8000);
                    }
                    return results.join('\\n\\n====================\\n\\n');
                }""")
                
                combined_data += f"\n\n### نتائج البحث عن الكلمة: {kw} ###\n" + extracted
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
    هذه بيانات حية مسحوبة من مكتبة إعلانات فيسبوك، مقسمة حسب كل إعلان مع رقم تعريفه (ID) وروابطه:
    {raw_data}
    
    استخرج لي "تقرير أفضل المنتجات الرابحة اليوم" (اختر أفضل 5 منتجات حقيقية وتجاهل الإعلانات غير التجارية).
    لكل منتج اذكر بوضوح تام وبنفس هذا الترتيب:
    1. 📦 اسم المنتج وفكرته وتفاصيل السعر/العرض.
    2. 🏪 اسم الصفحة المعلنة ورابطها (إن وجد في الروابط المرفقة).
    3. 🖼 رابط رؤية الإعلان والصور/الفيديو مباشرة: خذ رقم الإعلان (ID) وضعه في هذا الرابط:
       https://www.facebook.com/ads/library/?id=PUT_ID_HERE
       (استبدل PUT_ID_HERE برقم الإعلان الحقيقي ليظهر كرابط قابل للضغط).
    4. 🛒 رابط صفحة الهبوط (المتجر الإلكتروني): ضع الرابط الخارجي للمتجر المرفق مع الإعلان (أو اكتب "البيع عبر رسائل الصفحة" إذا كان الرابط يوجه إلى فيسبوك/ماسنجر/واتساب فقط).
    5. 📈 تاريخ بدء الإعلان ولماذا تراه منتجاً رابحاً؟
    """
    
    response = model.generate_content(prompt)
    send_telegram_report(f"🕵️‍♂️ تقرير التجسس اليومي (مدعم بروابط الصور والمتاجر):\n\n{response.text}")
    print("تم إرسال التقرير بنجاح!")

if __name__ == "__main__":
    main()
