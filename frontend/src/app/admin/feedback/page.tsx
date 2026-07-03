import { ProtectedRoute } from "@/features/auth";
import { AdminFeedbackScreen } from "@/screens/admin-feedback";

export default function Page() {
  return (
    <ProtectedRoute allowedRoles={["admin"]}>
      <AdminFeedbackScreen />
    </ProtectedRoute>
  );
}
