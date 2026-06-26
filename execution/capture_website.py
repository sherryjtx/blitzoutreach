import os
import sys
import argparse
import tempfile
import shutil
from playwright.sync_api import sync_playwright

def capture_website(url: str, output_path: str):
    """
    Captures a dynamic, smooth-scrolling video of a website using headless Playwright.
    Records viewport at 1080p, scrolls down the page over 12 seconds, and saves the video.
    """
    print(f"📹 Recording website scroll for {url}...")
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        
    temp_dir = tempfile.mkdtemp()
    
    with sync_playwright() as p:
        # Launch headless Chromium
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--font-render-hinting=none"
            ]
        )
        
        # Create context with video recording enabled
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            record_video_dir=temp_dir,
            record_video_size={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        
        # Inject cookie hiding styles
        page.add_init_script("""
            window.addEventListener('DOMContentLoaded', () => {
                const style = document.createElement('style');
                style.innerHTML = `
                    /* Common cookie banners and popups */
                    [id*="cookie" i], [class*="cookie" i], 
                    [id*="consent" i], [class*="consent" i],
                    [id*="banner" i], [class*="banner" i] {
                        display: none !important;
                    }
                `;
                document.head.appendChild(style);
            });
        """)
        
        try:
            # Navigate using domcontentloaded to prevent long loading delays from tracking pixels
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
        except Exception as e:
            print(f"⚠️ Navigation timeout/error (recording anyway): {e}")
            
        page.wait_for_timeout(1000)  # Settle time
        
        # Perform smooth cinematic scroll
        try:
            print("   Scrolling website...")
            page.evaluate("""
                async () => {
                    const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
                    const smoothScrollTo = (targetY, duration) => {
                        return new Promise((resolve) => {
                            const startY = window.scrollY;
                            const difference = targetY - startY;
                            const startTime = performance.now();
                            
                            function step(timestamp) {
                                const elapsed = timestamp - startTime;
                                const progress = Math.min(elapsed / duration, 1);
                                // easeInOutQuad curve
                                const ease = progress < 0.5 ? 2 * progress * progress : -1 + (4 - 2 * progress) * progress;
                                window.scrollTo(0, startY + ease * difference);
                                if (progress < 1) {
                                    requestAnimationFrame(step);
                                } else {
                                    resolve();
                                }
                            }
                            requestAnimationFrame(step);
                        });
                    };

                    // 1. Fully loaded settle time (1.5 seconds)
                    await delay(1500);

                    // 2. 4 micro-scrolls down (each 180px smoothly over 600ms, then pause 800ms)
                    await smoothScrollTo(180, 600);
                    await delay(800);
                    await smoothScrollTo(360, 600);
                    await delay(800);
                    await smoothScrollTo(540, 600);
                    await delay(800);
                    await smoothScrollTo(720, 600);
                    await delay(1200);

                    // 3. One smooth scroll back to top (scroll to 0 over 1200ms)
                    await smoothScrollTo(0, 1200);
                    await delay(1500); // end settle
                }
            """)
        except Exception as scroll_err:
            print(f"⚠️ Scrolling error: {scroll_err}")
            page.wait_for_timeout(12000) # Safe recording delay fallback
            
        # Get path to the recorded video before closing context
        video_path = page.video.path() if page.video else None
        
        context.close()
        browser.close()
        
        if video_path and os.path.exists(video_path):
            shutil.move(video_path, output_path)
            print(f"✅ Website video scroll saved to {output_path}")
        else:
            raise Exception("Playwright failed to record video.")
            
    # Cleanup temp directory
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture website scrolling video using Playwright.")
    parser.add_argument("url", help="Target website URL")
    parser.add_argument("output_path", help="Path to save the webm video")
    
    args = parser.parse_args()
    
    try:
        capture_website(args.url, args.output_path)
    except Exception as e:
        print(f"❌ Failed to capture website video: {e}")
        sys.exit(1)
