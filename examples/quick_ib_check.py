#!/usr/bin/env python3
"""Quick IB status check using browser-bunny persistent sessions"""

import asyncio
from browser_bunny.persistent_session_manager import get_persistent_session


async def quick_ib_check():
    """Quick check of IB status using persistent session."""
    print("🔍 Checking MarketBridge IB status...")
    
    # Get or create persistent session for MarketBridge monitoring
    manager = await get_persistent_session("marketbridge_monitor")
    
    try:
        # Navigate to MarketBridge UI (only if not already there)
        current_url = await manager.execute_js("(() => { return window.location.href; })()")
        if not current_url or "localhost:8080" not in current_url:
            print("📍 Navigating to MarketBridge UI...")
            await manager.navigate_to("http://localhost:8080", wait_until="domcontentloaded")
            await asyncio.sleep(1)  # Brief wait for page load
        else:
            print("📍 Already on MarketBridge UI")

        # Take screenshot for debugging
        await manager.screenshot("ib_status_check.png")

        # Check status with improved selectors
        status_script = """
        (() => {
            return {
                wsStatus: document.getElementById('ws-status-text')?.textContent?.trim(),
                ibStatus: document.getElementById('ib-status-text')?.textContent?.trim(),
                wsClass: document.getElementById('ws-status-indicator')?.className,
                ibClass: document.getElementById('ib-status-indicator')?.className,
                pageTitle: document.title,
                timestamp: new Date().toISOString()
            };
        })()
        """

        result = await manager.execute_js(status_script)
        
        if result:
            print("\n🔌 Connection Status:")
            print(f"  Page: {result.get('pageTitle', 'Unknown')}")
            print(f"  WS: {result.get('wsStatus', 'Not found')} [{result.get('wsClass', 'N/A')}]")
            print(f"  IB: {result.get('ibStatus', 'Not found')} [{result.get('ibClass', 'N/A')}]")
            print(f"  Checked at: {result.get('timestamp', 'Unknown')}")
            
            # Provide status interpretation
            ws_status = result.get('wsStatus', '').lower()
            ib_status = result.get('ibStatus', '').lower()
            
            # Check for positive connection status (avoid "not connected")
            ws_connected = 'connected' in ws_status and 'not connected' not in ws_status
            ib_connected = 'connected' in ib_status and 'not connected' not in ib_status
            
            if ws_connected and ib_connected:
                print("\n✅ All systems connected")
            elif ws_connected and not ib_connected:
                print("\n⚠️  WebSocket connected, IB connection issue")
            elif not ws_connected and ib_connected:
                print("\n⚠️  IB connected, WebSocket connection issue") 
            else:
                print("\n❌ Connection issues detected")
        else:
            print("❌ Failed to get status - page may not be loaded correctly")

    except Exception as e:
        print(f"❌ Error checking IB status: {e}")
        await manager.screenshot("ib_status_error.png")
        raise
    finally:
        # Don't cleanup - leave persistent session open for reuse
        await manager.cleanup()


if __name__ == "__main__":
    asyncio.run(quick_ib_check())
