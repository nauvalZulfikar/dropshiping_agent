export default function PrivacyPage() {
  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6 text-sm text-zinc-300 leading-relaxed">
      <h1 className="text-2xl font-bold text-white">Privacy Policy</h1>
      <p className="text-zinc-500">Last updated: April 18, 2026</p>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-white">1. Introduction</h2>
        <p>
          Aureon Forge (&quot;we&quot;, &quot;us&quot;, &quot;our&quot;) operates Aureon Dropship (&quot;the
          Service&quot;). This Privacy Policy explains how we collect, use, store,
          and protect your information when you use the Service.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-white">2. Information We Collect</h2>

        <h3 className="font-medium text-zinc-200">2.1 Information You Provide</h3>
        <ul className="list-disc pl-5 space-y-1">
          <li>Account credentials for connected platforms (TikTok, Instagram, Shopee, etc.)</li>
          <li>Product information (names, prices, descriptions, images)</li>
          <li>Content you create or upload (videos, captions, scripts)</li>
        </ul>

        <h3 className="font-medium text-zinc-200 mt-3">2.2 Information from Third-Party Platforms</h3>
        <p>When you connect a third-party account, we may receive:</p>
        <ul className="list-disc pl-5 space-y-1">
          <li><strong className="text-zinc-200">TikTok:</strong> User profile (display name, username, avatar), video publishing permissions. Scopes: user.info.basic, video.upload, video.publish.</li>
          <li><strong className="text-zinc-200">Instagram:</strong> Business account info, publishing permissions.</li>
          <li><strong className="text-zinc-200">Shopee/Tokopedia:</strong> Order data, product listings, inventory levels.</li>
        </ul>

        <h3 className="font-medium text-zinc-200 mt-3">2.3 Automatically Collected</h3>
        <ul className="list-disc pl-5 space-y-1">
          <li>Analytics data (content performance, engagement metrics) from connected platforms.</li>
          <li>Usage data for improving the Service.</li>
        </ul>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-white">3. How We Use Your Information</h2>
        <ul className="list-disc pl-5 space-y-1">
          <li>To publish content to your connected social media accounts on your behalf.</li>
          <li>To generate AI-powered content (scripts, listings, captions) based on your products.</li>
          <li>To process and fulfill orders through connected marketplace platforms.</li>
          <li>To provide analytics, insights, and optimization recommendations.</li>
          <li>To send notifications about orders, inventory, and system events.</li>
        </ul>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-white">4. Data Storage and Security</h2>
        <ul className="list-disc pl-5 space-y-1">
          <li>Access tokens are stored in encrypted, server-side cookies (AES-256-GCM) or encrypted environment variables. They are never exposed to the browser.</li>
          <li>We do not store your third-party platform passwords.</li>
          <li>Data is transmitted over HTTPS/TLS.</li>
          <li>Database credentials and API keys are stored in secured server environments.</li>
        </ul>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-white">5. Data Sharing</h2>
        <p>We do not sell, rent, or share your personal data with third parties except:</p>
        <ul className="list-disc pl-5 space-y-1">
          <li>With third-party platforms you have explicitly connected (e.g., TikTok, Shopee) to perform actions you requested.</li>
          <li>With AI service providers (OpenAI) to generate content — only product information is sent, never personal data.</li>
          <li>When required by law or legal process.</li>
        </ul>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-white">6. Your Rights</h2>
        <p>You have the right to:</p>
        <ul className="list-disc pl-5 space-y-1">
          <li><strong className="text-zinc-200">Disconnect</strong> any third-party account at any time, which revokes our access.</li>
          <li><strong className="text-zinc-200">Request deletion</strong> of your data by contacting us.</li>
          <li><strong className="text-zinc-200">Access</strong> information we hold about you.</li>
          <li><strong className="text-zinc-200">Revoke permissions</strong> directly through the third-party platform settings (e.g., TikTok &gt; Settings &gt; Security &gt; Manage App Permissions).</li>
        </ul>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-white">7. Data Retention</h2>
        <p>
          We retain your data for as long as your account is active. When you
          disconnect a third-party account, associated access tokens are
          immediately deleted. You may request full data deletion at any time.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-white">8. Children&apos;s Privacy</h2>
        <p>
          The Service is not intended for users under the age of 18. We do not
          knowingly collect personal information from minors.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-white">9. Changes to This Policy</h2>
        <p>
          We may update this Privacy Policy from time to time. Changes will be
          posted on this page with an updated revision date.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-white">10. Contact</h2>
        <p>
          For privacy-related questions or data requests, contact us at{" "}
          <a href="mailto:privacy@aureonforge.com" className="text-blue-400 hover:underline">
            privacy@aureonforge.com
          </a>
        </p>
      </section>
    </div>
  );
}
