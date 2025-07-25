const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  try {
    await page.goto('http://localhost:3005', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    
    // 최종 스크린샷
    await page.screenshot({ 
      path: 'final-dashboard-screenshot.png', 
      fullPage: true
    });
    console.log('✅ 최종 스크린샷 저장 완료: final-dashboard-screenshot.png');
    
  } catch (error) {
    console.error('스크린샷 촬영 실패:', error);
  }
  
  await browser.close();
})();