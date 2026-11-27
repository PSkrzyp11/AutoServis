import { Alert, AlertDescription } from "@/components/ui/alert";

type StatusMessageProps = {
  tone: "error" | "success";
  message: string;
};

export function StatusMessage({ tone, message }: StatusMessageProps) {
  const isError = tone === "error";
  return (
    <Alert variant={isError ? "destructive" : "default"} role={isError ? "alert" : "status"}>
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}
