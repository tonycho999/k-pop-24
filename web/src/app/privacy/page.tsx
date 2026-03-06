export default function PrivacyPolicy() {
  return (
    <div className="container mx-auto px-4 max-w-4xl py-12 text-gray-200">
      <h1 className="text-3xl font-bold mb-8 text-white">Privacy Policy</h1>
      <p className="mb-6 text-gray-400">Last updated: {new Date().toLocaleDateString()}</p>

      <div className="space-y-8 text-sm md:text-base leading-relaxed">
        <section>
          <h2 className="text-xl font-semibold mb-3 text-white">1. Information We Collect</h2>
          <p>
            At K-Enter24, your privacy is important to us. We do not require users to create accounts or provide personal information to browse our content. We may collect non-personally identifiable information such as browser types, referring pages, and timestamp data for analytical purposes.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3 text-white">2. Cookies and Tracking</h2>
          <p>
            We may use cookies and similar tracking technologies to track activity on our service and hold certain information. This is primarily used to enhance user experience and analyze website traffic. You can instruct your browser to refuse all cookies or to indicate when a cookie is being sent.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3 text-white">3. Third-Party Services</h2>
          <p>
            Our website may contain links to other sites (such as original news sources) that are not operated by us. We strongly advise you to review the Privacy Policy of every site you visit. We have no control over and assume no responsibility for the content, privacy policies, or practices of any third-party sites or services.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3 text-white">4. Contact Us</h2>
          <p>
            If you have any questions or suggestions about our Privacy Policy, do not hesitate to contact us at: <a href="mailto:admin@k-enter24.com" className="text-blue-400 hover:underline">admin@k-enter24.com</a>
          </p>
        </section>
      </div>
    </div>
  );
}
