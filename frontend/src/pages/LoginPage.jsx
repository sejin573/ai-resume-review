import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setToken } from "../api/client";
import AuthForm from "../components/AuthForm";

export default function LoginPage() {
  const navigate = useNavigate();
  const [values, setValues] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onChange = (event) => {
    setValues((prev) => ({ ...prev, [event.target.name]: event.target.value }));
  };

  const onSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = await api.login(values);
      setToken(data.access_token);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthForm
      title="로그인"
      subtitle="이전 첨삭 결과와 개선 이력을 이어서 관리할 수 있습니다."
      fields={[
        { name: "email", label: "이메일", type: "email", placeholder: "you@example.com", required: true },
        { name: "password", label: "비밀번호", type: "password", placeholder: "8자 이상", required: true },
      ]}
      values={values}
      error={error}
      loading={loading}
      submitLabel="로그인"
      footerText="아직 계정이 없나요?"
      footerLinkText="회원가입"
      footerLinkTo="/signup"
      onChange={onChange}
      onSubmit={onSubmit}
    />
  );
}
