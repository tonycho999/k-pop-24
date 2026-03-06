export default function TermsOfService() {
  return (
    <div className="container mx-auto px-4 max-w-4xl py-12 text-gray-200">
      <h1 className="text-3xl font-bold mb-8 text-white">Terms of Service</h1>
      <p className="mb-6 text-gray-400">Last updated: {new Date().toLocaleDateString()}</p>

      <div className="space-y-8 text-sm md:text-base leading-relaxed">
        <section>
          <h2 className="text-xl font-semibold mb-3 text-white">1. Acceptance of Terms</h2>
          <p>
            By accessing and using K-Enter24, you agree to be bound by these Terms of Service. If you do not agree with any part of these terms, please do not use our website.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3 text-white">2. Content Disclaimer</h2>
          <p>
            K-Enter24 is an automated news aggregation platform. The articles, summaries, and headlines provided on this website are generated using Artificial Intelligence (AI) algorithms based on real-time search trends and public news sources. 
            While we strive for accuracy, we do not guarantee the absolute correctness, completeness, or reliability of the AI-generated content. All original copyrights belong to their respective publishers.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3 text-white">3. Intellectual Property</h2>
          <p>
            The website design, logos, and custom code are the property of K-Enter24. The news content and images displayed are aggregated for informational purposes under fair use principles. If you are a copyright owner and wish to have your content removed, please contact us.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3 text-white">4. Limitation of Liability</h2>
          <p>
            K-Enter24 and its operators shall not be held liable for any direct, indirect, incidental, or consequential damages resulting from the use or inability to use our services, or from relying on the information provided on this site.
          </p>
        </section>
      </div>
    </div>
  );
}
