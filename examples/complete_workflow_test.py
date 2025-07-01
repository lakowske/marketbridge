#!/usr/bin/env python3
"""Complete subscribe → unsubscribe workflow test"""

import asyncio
import sys
from browser_bunny.persistent_session_manager import get_persistent_session


async def complete_workflow_test(symbol: str = "AAPL", instrument_type: str = "STK"):
    """Test the complete subscribe → inspect → unsubscribe workflow."""
    print(f"🔄 Testing complete workflow for {symbol} ({instrument_type})")
    print("=" * 60)
    
    manager = await get_persistent_session("marketbridge")
    
    try:
        # Navigate to MarketBridge
        await manager.navigate_to("http://localhost:8080", wait_until="domcontentloaded")
        
        # Step 1: Check initial state
        print("\n📋 STEP 1: Check initial state")
        initial_state = await check_state(manager, "initial")
        print(f"Initial subscriptions: {len(initial_state['subscriptions'])}")
        print(f"Initial market data: {len(initial_state['market_data'])}")
        
        # Step 2: Subscribe
        print(f"\n📈 STEP 2: Subscribe to {symbol}")
        await subscribe_symbol(manager, symbol, instrument_type)
        
        # Step 3: Check state after subscription
        print("\n📋 STEP 3: Check state after subscription")
        await asyncio.sleep(2)  # Give time for subscription to process
        post_subscribe_state = await check_state(manager, "post_subscribe")
        
        subscription_success = len(post_subscribe_state['subscriptions']) > 0
        market_data_success = len(post_subscribe_state['market_data']) > 0
        
        print(f"Subscription found: {subscription_success}")
        print(f"Market data found: {market_data_success}")
        
        if subscription_success:
            print("✅ Subscription successful!")
            
            # Step 4: Test proper unsubscribe
            print(f"\n📉 STEP 4: Unsubscribe from {symbol}")
            unsubscribe_success = await unsubscribe_symbol(manager, symbol)
            
            # Step 5: Check final state
            print("\n📋 STEP 5: Check state after unsubscribe")
            await asyncio.sleep(3)  # Give time for unsubscribe to process
            final_state = await check_state(manager, "final")
            
            final_subscription_gone = len(final_state['subscriptions']) == 0
            print(f"Subscription removed: {final_subscription_gone}")
            print(f"Unsubscribe message sent: {unsubscribe_success}")
            
            if final_subscription_gone and unsubscribe_success:
                print("\n🎉 COMPLETE WORKFLOW SUCCESS!")
                print("  ✅ Subscribe worked")
                print("  ✅ Unsubscribe worked")
                print("  ✅ Backend properly notified")
                return True
            else:
                print("\n⚠️  PARTIAL SUCCESS")
                print(f"  Subscribe: {'✅' if subscription_success else '❌'}")
                print(f"  Unsubscribe UI: {'✅' if final_subscription_gone else '❌'}")
                print(f"  Unsubscribe Backend: {'✅' if unsubscribe_success else '❌'}")
                return False
        else:
            print("❌ Subscription failed - skipping unsubscribe test")
            return False
            
    except Exception as e:
        print(f"❌ Error during workflow test: {e}")
        await manager.screenshot("error_workflow_test.png")
        raise
    finally:
        await manager.cleanup()


async def check_state(manager, stage_name):
    """Check current subscription and market data state."""
    await manager.screenshot(f"state_check_{stage_name}.png")
    
    state = await manager.execute_js("""
    (() => {
        const subscriptionsList = document.querySelector('#subscriptions-list');
        const marketDataGrid = document.querySelector('#market-data-grid');
        
        let subscriptions = [];
        let marketData = [];
        
        // Check subscriptions (look for checkboxes)
        if (subscriptionsList) {
            const checkboxes = subscriptionsList.querySelectorAll('input[type="checkbox"]');
            checkboxes.forEach(checkbox => {
                const parentItem = checkbox.closest('.subscription-item, li, div');
                if (parentItem) {
                    subscriptions.push({
                        value: checkbox.value,
                        text: parentItem.textContent?.trim(),
                        checked: checkbox.checked
                    });
                }
            });
        }
        
        // Check market data
        if (marketDataGrid) {
            const rows = marketDataGrid.querySelectorAll('tbody tr');
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length > 0 && cells[0].textContent?.trim()) {
                    const symbol = cells[0].textContent.trim();
                    if (!symbol.includes('No market data')) {
                        marketData.push({
                            symbol: symbol,
                            last: cells[1]?.textContent?.trim() || '',
                            bid: cells[2]?.textContent?.trim() || '',
                            ask: cells[3]?.textContent?.trim() || ''
                        });
                    }
                }
            });
        }
        
        return {
            subscriptions: subscriptions,
            market_data: marketData,
            timestamp: new Date().toISOString()
        };
    })()
    """)
    
    print(f"  📊 State at {stage_name}:")
    for sub in state.get('subscriptions', []):
        print(f"    📋 Subscription: {sub['text']}")
    for data in state.get('market_data', []):
        print(f"    📈 Market Data: {data['symbol']} (Last: {data['last']}, Bid: {data['bid']})")
    
    return state


async def subscribe_symbol(manager, symbol, instrument_type):
    """Subscribe to a symbol."""
    # Map instrument types
    instrument_mapping = {
        "STK": "stock",
        "FUT": "future",
        "OPT": "option",
        "CASH": "forex",
    }
    ui_instrument_type = instrument_mapping.get(instrument_type.upper(), "stock")
    
    # Fill form and subscribe
    await manager.execute_js(f"""
    (() => {{
        // Fill symbol
        const symbolInput = document.querySelector('#symbol');
        if (symbolInput) {{
            symbolInput.value = '{symbol}';
            symbolInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}
        
        // Set instrument type
        const instrumentSelect = document.querySelector('#instrument-type');
        if (instrumentSelect) {{
            instrumentSelect.value = '{ui_instrument_type}';
            instrumentSelect.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}
        
        // Click subscribe
        const subscribeBtn = document.querySelector('#subscribe-btn');
        if (subscribeBtn) {{
            subscribeBtn.click();
        }}
    }})()
    """)
    print(f"  📝 Subscription form submitted for {symbol}")


async def unsubscribe_symbol(manager, symbol):
    """Properly unsubscribe from a symbol by selecting checkbox and clicking unsubscribe."""
    # Monitor WebSocket messages
    await manager.execute_js("""
    (() => {
        window.unsubscribeMessages = [];
        if (window.wsClient && window.wsClient.ws) {
            const originalSend = window.wsClient.ws.send;
            window.wsClient.ws.send = function(data) {
                console.log('📤 WebSocket SEND:', data);
                window.unsubscribeMessages.push({
                    data: data,
                    timestamp: new Date().toISOString()
                });
                return originalSend.call(this, data);
            };
        }
    })()
    """)
    
    # Select checkbox and unsubscribe
    result = await manager.execute_js(f"""
    (() => {{
        const targetSymbol = '{symbol}';
        const subscriptionsList = document.querySelector('#subscriptions-list');
        
        if (!subscriptionsList) {{
            return {{ success: false, message: 'Subscriptions list not found' }};
        }}
        
        // Find checkbox for target symbol
        const checkboxes = subscriptionsList.querySelectorAll('input[type="checkbox"]');
        let targetCheckbox = null;
        
        for (const checkbox of checkboxes) {{
            const parentItem = checkbox.closest('.subscription-item, li, div');
            if (parentItem && parentItem.textContent.includes(targetSymbol)) {{
                targetCheckbox = checkbox;
                break;
            }}
        }}
        
        if (!targetCheckbox) {{
            return {{ success: false, message: `No checkbox found for ${{targetSymbol}}` }};
        }}
        
        // Select the checkbox
        targetCheckbox.checked = true;
        targetCheckbox.dispatchEvent(new Event('change', {{ bubbles: true }}));
        
        // Click unsubscribe button
        const unsubscribeBtn = document.querySelector('#unsubscribe-btn');
        if (!unsubscribeBtn) {{
            return {{ success: false, message: 'Unsubscribe button not found' }};
        }}
        
        unsubscribeBtn.click();
        
        return {{ 
            success: true, 
            message: `Selected checkbox and clicked unsubscribe for ${{targetSymbol}}`
        }};
    }})()
    """)
    
    print(f"  📤 Unsubscribe action: {result.get('message', 'Unknown')}")
    
    # Check if WebSocket message was sent
    await asyncio.sleep(1)
    messages = await manager.execute_js("""
    (() => {
        return {
            messages: window.unsubscribeMessages || [],
            count: window.unsubscribeMessages ? window.unsubscribeMessages.length : 0
        };
    })()
    """)
    
    message_sent = messages.get('count', 0) > 0
    if message_sent:
        for msg in messages.get('messages', []):
            print(f"  📤 WebSocket: {msg['data']}")
    
    return result.get('success', False) and message_sent


if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    instrument = sys.argv[2] if len(sys.argv) > 2 else "STK"
    
    success = asyncio.run(complete_workflow_test(symbol, instrument))
    if not success:
        sys.exit(1)