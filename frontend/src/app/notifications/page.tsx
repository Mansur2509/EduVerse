import { ProtectedRoute } from "@/features/auth";
import { NotificationsScreen } from "@/screens/notifications";

export default function Page() {
  return (
    <ProtectedRoute>
      <NotificationsScreen />
    </ProtectedRoute>
  );
}
