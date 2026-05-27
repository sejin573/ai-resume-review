import { useState } from "react";
import Button from "./Button";

export default function CopyButton({ text, label = "복사" }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  };

  return <Button variant="ghost" onClick={handleCopy}>{copied ? "복사됨" : label}</Button>;
}
