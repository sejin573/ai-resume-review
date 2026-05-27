import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setToken } from "../api/client";
import AuthForm from "../components/AuthForm";

export default function SignupPage() {
  const navigate = useNavigate();
  const [values, setValues] = useState({ email: "", password: "", full_name: "" });
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
      const data = await api.signup(values);
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
      title="회원가입"
      subtitle="첨삭 이력과 동의 기반 학습 데이터 수집 여부를 분리해서 안전하게 관리합니다."
      fields={[
        { name: "full_name", label: "이름", type: "text", placeholder: "선택 입력" },
        { name: "email", label: "이메일", type: "email", placeholder: "you@example.com", required: true },
        { name: "password", label: "비밀번호", type: "password", placeholder: "8자 이상", required: true },
      ]}
      values={values}
      error={error}
      loading={loading}
      submitLabel="회원가입"
      footerText="이미 계정이 있나요?"
      footerLinkText="로그인"
      footerLinkTo="/login"
      onChange={onChange}
      onSubmit={onSubmit}
    />
  );
}
