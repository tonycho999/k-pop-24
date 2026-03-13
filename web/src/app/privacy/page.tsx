'use client';

export default function PrivacyPolicy() {
  const lastUpdated = "March 13, 2026";

  return (
    <div className="container mx-auto px-4 max-w-4xl py-12 text-slate-300">
      <h1 className="text-4xl font-black mb-4 text-white tracking-tight">Privacy Policy</h1>
      <p className="mb-10 text-slate-500 font-medium">Last updated: {lastUpdated}</p>

      <div className="space-y-10 text-sm md:text-base leading-relaxed">
        {/* 1. Introduction */}
        <section>
          <h2 className="text-2xl font-bold mb-4 text-white">1. Introduction</h2>
          <p>
            Welcome to K-Enter24 ("we," "our," or "us"). We are committed to protecting your personal information and your right to privacy. 
            This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you visit our website 
            <span className="text-cyan-400"> k-enter24.com</span>. Please read this privacy policy carefully. If you do not agree with the terms of this privacy policy, please do not access the site.
          </p>
        </section>

        {/* 2. Information We Collect */}
        <section>
          <h2 className="text-2xl font-bold mb-4 text-white">2. Information We Collect</h2>
          <div className="space-y-4">
            <p><strong>Personal Data:</strong> We do not require account registration for basic browsing. However, if you sign in via Google OAuth, we may collect your name, email address, and profile picture provided by Google to personalize your experience and manage your votes/likes.</p>
            <p><strong>Derivative Data:</strong> Our servers automatically collect information when you access the site, such as your IP address, browser type, operating system, access times, and the pages you have viewed directly before and after accessing the site.</p>
            <p><strong>Mobile Device Data:</strong> If you access the site from a mobile device, we may collect device information such as your mobile device ID, model, and manufacturer.</p>
          </div>
        </section>

        {/* 3. Use of Your Information */}
        <section>
          <h2 className="text-2xl font-bold mb-4 text-white">3. Use of Your Information</h2>
          <p className="mb-4">Having accurate information about you permits us to provide you with a smooth, efficient, and customized experience. Specifically, we may use information collected about you via the site to:</p>
          <ul className="list-disc pl-6 space-y-2 text-slate-400">
            <li>Create and manage your account (Likes, Voting history).</li>
            <li>Deliver targeted advertising, coupons, newsletters, and other information regarding promotions and the site to you.</li>
            <li>Generate a personal profile about you to make future visits to the site more personalized.</li>
            <li>Increase the efficiency and operation of the site.</li>
            <li>Monitor and analyze usage and trends to improve your experience with the site.</li>
          </ul>
        </section>

        {/* 4. Disclosure of Your Information */}
        <section>
          <h2 className="text-2xl font-bold mb-4 text-white">4. Disclosure of Your Information</h2>
          <p>We may share information we have collected about you in certain situations. Your information may be disclosed as follows: By Law or to Protect Rights, Business Transfers, Third-Party Service Providers, and Marketing Communications (with your consent).</p>
        </section>

        {/* 5. Tracking Technologies (Cookies) */}
        <section>
          <h2 className="text-2xl font-bold mb-4 text-white">5. Tracking Technologies</h2>
          <p>
            We may use cookies, web beacons, tracking pixels, and other tracking technologies on the site to help customize the site and improve your experience. 
            When you access the site, your personal information is not collected through the use of tracking technology. 
            Most browsers are set to accept cookies by default. You can remove or reject cookies, but be aware that such action could affect the availability and functionality of the site.
          </p>
        </section>

        {/* 6. Third-Party Advertisers */}
        <section>
          <h2 className="text-2xl font-bold mb-4 text-white">6. Third-Party Advertisers</h2>
          <p>
            We use third-party advertising companies (such as Involve Asia, Shopee, and Amazon) to serve ads when you visit the site. 
            These companies may use information about your visits to the site and other websites that are contained in web cookies in order to provide advertisements about goods and services of interest to you. 
            We do not have control over the cookies used by these third-party advertisers.
          </p>
        </section>

        {/* 7. Security of Your Information */}
        <section>
          <h2 className="text-2xl font-bold mb-4 text-white">7. Security of Your Information</h2>
          <p>
            We use administrative, technical, and physical security measures to help protect your personal information. 
            While we have taken reasonable steps to secure the personal information you provide to us, please be aware that despite our efforts, 
            no security measures are perfect or impenetrable, and no method of data transmission can be guaranteed against any interception or other type of misuse.
          </p>
        </section>

        {/* 8. Contact Us */}
        <section className="p-8 bg-slate-900 rounded-[32px] border border-slate-800">
          <h2 className="text-xl font-bold mb-3 text-white">8. Contact Us</h2>
          <p className="mb-4 text-slate-400">If you have questions or comments about this Privacy Policy, please contact us at:</p>
          <div className="text-cyan-400 font-bold">
            <p>Email: admin@k-enter24.com</p>
          </div>
        </section>
      </div>
    </div>
  );
}
