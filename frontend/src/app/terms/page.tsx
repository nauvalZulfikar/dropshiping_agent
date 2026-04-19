export default function TermsPage() {
  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6 text-sm text-zinc-300 leading-relaxed">
      <h1 className="text-2xl font-bold text-white">Terms of Service</h1>
      <p className="text-zinc-500">Last updated: April 18, 2026</p>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-white">1. Acceptance of Terms</h2>
        <p>
          By accessing or using Aureon Dropship (&quot;the Service&quot;), operated by
          Aureon Forge (&quot;we&quot;, &quot;us&quot;, &quot;our&quot;), you agree to be bound by these
          Terms of Service. If you do not agree, do not use the Service.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-white">2. Description of Service</h2>
        <p>
          Aureon Dropship is a dropshipping automation platform that provides
          product discovery, content creation, social media publishing,
          inventory management, order fulfillment, and analytics tools. The
          Service integrates with third-party platforms including TikTok,
          Instagram, Shopee, Tokopedia, and others.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-white">3. Account Responsibilities</h2>
        <ul className="list-disc pl-5 space-y-1">
          <li>You must provide accurate information when connecting third-party accounts.</li>
          <li>You are responsible for maintaining the security of your account credentials.</li>
          <li>You must comply with the terms of service of all connected third-party platforms.</li>
          <li>You are solely responsible for all content published through the Service.</li>
        </ul>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-white">4. Third-Party Integrations</h2>
        <p>
          The Service connects to third-party platforms (TikTok, Instagram,
          Shopee, etc.) via their official APIs. We access only the permissions
          you explicitly grant. You may revoke access at any time through the
          Service or the third-party platform&apos;s settings.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-white">5. Content and Intellectual Property</h2>
        <ul className="list-disc pl-5 space-y-1">
          <li>You retain ownership of all content you create or upload.</li>
          <li>You grant us a limited license to process and publish content on your behalf.</li>
          <li>AI-generated content (scripts, listings, captions) is provided as-is. You are responsible for reviewing before publishing.</li>
          <li>You must not use the Service to create or distribute content that violates applicable laws or third-party rights.</li>
        </ul>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-white">6. Prohibited Use</h2>
        <p>You may not use the Service to:</p>
        <ul className="list-disc pl-5 space-y-1">
          <li>Violate any applicable laws or regulations.</li>
          <li>Infringe on intellectual property rights of others.</li>
          <li>Distribute misleading, fraudulent, or harmful content.</li>
          <li>Attempt to gain unauthorized access to the Service or its systems.</li>
          <li>Resell or redistribute the Service without authorization.</li>
        </ul>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-white">7. Limitation of Liability</h2>
        <p>
          The Service is provided &quot;as is&quot; without warranties of any kind. We
          are not liable for any indirect, incidental, or consequential damages
          arising from your use of the Service, including but not limited to
          loss of revenue, data, or business opportunities.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-white">8. Termination</h2>
        <p>
          We may suspend or terminate your access to the Service at any time
          for violation of these terms. You may stop using the Service and
          disconnect all integrations at any time.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-white">9. Changes to Terms</h2>
        <p>
          We may update these Terms from time to time. Continued use of the
          Service after changes constitutes acceptance of the updated Terms.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-white">10. Contact</h2>
        <p>
          For questions about these Terms, contact us at{" "}
          <a href="mailto:support@aureonforge.com" className="text-blue-400 hover:underline">
            support@aureonforge.com
          </a>
        </p>
      </section>
    </div>
  );
}
