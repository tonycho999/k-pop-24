import Link from 'next/link';

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-gray-900 text-gray-400 py-8 border-t border-gray-800 mt-12">
      <div className="container mx-auto px-4 max-w-7xl">
        <div className="flex flex-col md:flex-row justify-between items-center">
          
          {/* Logo & Copyright */}
          <div className="mb-4 md:mb-0 text-center md:text-left">
            <p className="text-lg font-bold text-white tracking-wider mb-1">
              K-ENTER<span className="text-blue-500">24</span>
            </p>
            <p className="text-sm">
              &copy; {currentYear} K-Enter24. All rights reserved.
            </p>
          </div>

          {/* Legal Links */}
          <div className="flex space-x-6 text-sm">
            <Link href="/terms" className="hover:text-white transition-colors">
              Terms of Service
            </Link>
            <Link href="/privacy" className="hover:text-white transition-colors">
              Privacy Policy
            </Link>
            {/* 💡 대표님 이메일 적용 완료 */}
            <a href="mailto:admin@k-enter24.com" className="hover:text-white transition-colors">
              Contact
            </a>
          </div>
          
        </div>
      </div>
    </footer>
  );
}
