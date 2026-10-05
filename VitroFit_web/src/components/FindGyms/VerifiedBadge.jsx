import './VerifiedBadge.css';

/** Shown on gyms whose details an admin/owner approved (see isVerifiedSource). */
export default function VerifiedBadge() {
  return (
    <span className="verified-badge" title="Details reviewed and approved by an admin or gym owner">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <path d="M9 12l2 2 4-4" />
      </svg>
      Verified
    </span>
  );
}
