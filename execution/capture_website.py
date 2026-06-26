import os
import sys
import time
import argparse
import tempfile
import shutil
import subprocess
from playwright.sync_api import sync_playwright

def capture_website(url: str, output_path: str, screenshot_path: str = None):
    """
    Captures a dynamic, smooth-scrolling video of a website using headless Playwright.
    Records viewport at 1080p, waits for full page load, captures a cover screenshot,
    scrolls down/up the page, and trims the loading frames from the final output video.
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
                "--font-render-hinting=none",
                "--autoplay-policy=no-user-gesture-required"
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
        
        # Track start time to measure loading duration precisely
        start_time = time.time()
        navigation_success = True
        try:
            # Navigate using domcontentloaded for fast, reliable page loading
            # Set timeout to 30 seconds to avoid long hangs on slower servers
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            print("   Page HTML loaded.")
            page.wait_for_timeout(3000) # Settle time
            
            # Force autoplay all videos on the page (e.g. background videos)
            try:
                page.evaluate("""
                    document.querySelectorAll('video').forEach(v => {
                        v.muted = true;
                        v.setAttribute('autoplay', 'true');
                        v.setAttribute('playsinline', 'true');
                        v.play().catch(e => {});
                    });
                """)
                print("   Forced background video autoplay.")
            except Exception as vid_err:
                print(f"   Failed to force video autoplay: {vid_err}")
                
            load_duration = time.time() - start_time
            print(f"   Website fully settled in {load_duration:.2f} seconds.")
        except Exception as e:
            print(f"⚠️ Navigation timeout/error (loading branded fallback page): {e}")
            navigation_success = False
            
        if not navigation_success:
            # Try to extract clean company name from URL
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                company_name = domain.replace("www.", "").split(".")[0].title()
            except:
                company_name = "your team"
                
            # Create a clean fallback HTML page to display instead of a blank hang
            fallback_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
            <meta charset="utf-8">
            <style>
              body {{
                background-color: #050506;
                color: #fafafa;
                font-family: 'Outfit', sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
                overflow: hidden;
              }}
              .card {{
                background: rgba(255, 255, 255, 0.02);
                backdrop-filter: blur(12px);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 20px;
                padding: 60px 80px;
                text-align: center;
                box-shadow: 0 30px 60px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05);
                max-width: 700px;
              }}
              h1 {{ font-size: 36px; font-weight: 700; margin-bottom: 15px; letter-spacing: -0.02em; color: #ef4444; }}
              p {{ color: rgba(255, 255, 255, 0.6); font-size: 20px; line-height: 1.6; margin: 0; }}
            </style>
            </head>
            <body>
              <div class="card">
                <h1>Interactive Presentation</h1>
                <p>Prepared especially for the team at {company_name}</p>
              </div>
            </body>
            </html>
            """
            fallback_path = os.path.join(temp_dir, "fallback.html")
            with open(fallback_path, "w", encoding="utf-8") as f:
                f.write(fallback_content)
            page.goto(f"file:///{fallback_path.replace('\\', '/')}", wait_until="load")
            page.wait_for_timeout(1000)
            load_duration = 1.5 # Fixed short trim duration for fallback page
            print(f"   Branded fallback page loaded successfully.")
            
        # Capture cover screenshot of the fully loaded page (before scrolling)
        if screenshot_path:
            try:
                os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                page.screenshot(path=screenshot_path, full_page=False)
                print(f"📸 Saved cover screenshot to {screenshot_path}")
            except Exception as ss_err:
                print(f"⚠️ Failed to capture cover screenshot: {ss_err}")
        
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
            # Trim the first `load_duration` seconds (the blank loading phase)
            print(f"✂️ Trimming the first {load_duration:.2f} seconds of loading frames...")
            cmd_trim = [
                "ffmpeg", "-y",
                "-ss", f"{load_duration:.2f}",
                "-i", video_path,
                "-c", "copy",
                output_path
            ]
            subprocess.run(cmd_trim, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            print(f"✅ Website video scroll saved and trimmed to {output_path}")
        else:
            raise Exception("Playwright failed to record video.")
            
    # Cleanup temp directory
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture website scrolling video using Playwright.")
    parser.add_argument("url", help="Target website URL")
    parser.add_argument("output_path", help="Path to save the webm video")
    parser.add_argument("--screenshot", help="Optional path to save cover screenshot")
    
    args = parser.parse_args()
    
    try:
        capture_website(args.url, args.output_path, args.screenshot)
    except Exception as e:
        print(f"❌ Failed to capture website video: {e}")
        sys.exit(1)
