import os
import sys
import argparse
from playwright.sync_api import sync_playwright

def capture_website(url: str, output_path: str):
    """
    Captures a high-resolution screenshot of a website using headless Playwright.
    Waits for network to be idle to ensure assets are loaded, with a fallback timeout.
    """
    print(f"📸 Capturing screenshot for {url}...")
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        
    with sync_playwright() as p:
        # Launch headless Chromium with standard args
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--font-render-hinting=none"
            ]
        )
        
        # Create context with realistic desktop viewport and user agent
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        
        # Inject custom styles if needed (e.g. hiding cookie banners)
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
            # Navigate with 15-second timeout and wait for networkidle
            page.goto(url, wait_until="networkidle", timeout=15000)
        except Exception as e:
            # If networkidle times out, we still proceed to take the screenshot of whatever loaded
            print(f"⚠️ Navigation timeout/error (taking screenshot anyway): {e}")
            
        # Optional: Give a small extra pause for animations or rendering to settle
        page.wait_for_timeout(1000)
        
        # Capture screenshot
        page.screenshot(path=output_path, full_page=False)
        print(f"✅ Screenshot saved to {output_path}")
        
        browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture website screenshot using Playwright.")
    parser.add_argument("url", help="Target website URL")
    parser.add_argument("output_path", help="Path to save the screenshot")
    
    args = parser.parse_args()
    
    try:
        capture_website(args.url, args.output_path)
    except Exception as e:
        print(f"❌ Failed to capture screenshot: {e}")
        sys.exit(1)
