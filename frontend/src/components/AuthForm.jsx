import { Link } from "react-router-dom";

export default function AuthForm({
  title,
  subtitle,
  fields,
  values,
  error,
  loading,
  submitLabel,
  footerText,
  footerLinkText,
  footerLinkTo,
  onChange,
  onSubmit,
}) {
  return (
    <div className="auth-shell">
      <form className="auth-card" onSubmit={onSubmit}>
        <div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        {fields.map((field) => (
          <label key={field.name} className="field">
            <span>{field.label}</span>
            <input
              type={field.type}
              name={field.name}
              value={values[field.name]}
              onChange={onChange}
              placeholder={field.placeholder}
              required={field.required}
            />
          </label>
        ))}
        {error ? <div className="error-box">{error}</div> : null}
        <button className="primary-button" type="submit" disabled={loading}>
          {loading ? "처리 중..." : submitLabel}
        </button>
        <p className="muted">
          {footerText} <Link to={footerLinkTo}>{footerLinkText}</Link>
        </p>
      </form>
    </div>
  );
}
