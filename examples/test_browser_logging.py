#!/usr/bin/env python3
"""Test browser logging functionality by executing JavaScript that generates console logs."""
import asyncio

from browser_bunny.persistent_session_manager import get_persistent_session


async def main():
    print("Testing browser logging functionality...")

    # Get existing session
    manager = await get_persistent_session("marketbridge_ui")

    try:
        # Navigate to MarketBridge to ensure page is loaded
        await manager.navigate_to("http://localhost:8080")
        print("✅ Navigated to MarketBridge UI")

        # Wait a moment for the browser logger to initialize
        await asyncio.sleep(2)

        # Test different types of console logs
        print("🧪 Testing console.log...")
        await manager.execute_js(
            "console.log('Test message from browser - INFO level')"
        )

        print("🧪 Testing console.info...")
        await manager.execute_js(
            "console.info('Test info message with data:', {test: 'data', value: 42})"
        )

        print("🧪 Testing console.warn...")
        await manager.execute_js("console.warn('Test warning message')")

        print("🧪 Testing console.error...")
        await manager.execute_js(
            "console.error('Test error message', {error: 'details'})"
        )

        print("🧪 Testing console.debug...")
        await manager.execute_js("console.debug('Test debug message')")

        # Test manual logging through browser logger
        print("🧪 Testing browserLogger methods...")
        await manager.execute_js(
            """
            if (window.browserLogger) {
                browserLogger.logInfo('Manual info log via browserLogger');
                browserLogger.logWarning('Manual warning log via browserLogger');
                browserLogger.logError('Manual error log via browserLogger');
                browserLogger.logDebug('Manual debug log via browserLogger');
            } else {
                console.error('browserLogger not available!');
            }
        """
        )

        # Test complex object logging
        print("🧪 Testing complex object logging...")
        await manager.execute_js(
            """
            const complexObject = {
                user: 'testUser',
                timestamp: new Date(),
                data: {
                    symbols: ['AAPL', 'GOOGL', 'MSFT'],
                    prices: [150.25, 2800.50, 300.75]
                },
                actions: ['subscribe', 'unsubscribe']
            };
            console.info('Complex object test:', complexObject);
        """
        )

        # Force flush any remaining logs
        print("🧪 Flushing browser logs...")
        await manager.execute_js(
            """
            if (window.browserLogger) {
                browserLogger.flush();
                console.log('Browser logger flushed - queue size:', browserLogger.getQueueSize());
            }
        """
        )

        print("✅ Browser logging tests completed")
        print("📋 Check the logs/browser.log file to see the captured logs")

    finally:
        # Keep session alive
        await manager.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
