export default function PageLoader({ text }) {
  return (
    <div className="page-loader">
      <div className="page-loader-spinner" />
      <div className="page-loader-text">{text || 'Loading...'}</div>
    </div>
  );
}
