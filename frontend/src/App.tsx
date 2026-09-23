import { Center, Loader, Stack, Text } from "@mantine/core";
import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { authenticate } from "./api/client";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Documents } from "./pages/Documents";
import { PatientCard } from "./pages/PatientCard";
import { Visits } from "./pages/Visits";
import { useAuthStore } from "./store/auth";

export default function App() {
  const { status, error } = useAuthStore();

  useEffect(() => {
    window.Telegram?.WebApp?.ready();
    window.Telegram?.WebApp?.expand();
    void authenticate();
  }, []);

  if (status === "idle" || status === "loading") {
    return (
      <Center h="100vh">
        <Loader />
      </Center>
    );
  }

  if (status === "error") {
    return (
      <Center h="100vh" p="md">
        <Stack align="center" gap="xs">
          <Text fw={600}>Не получилось войти</Text>
          <Text c="dimmed" ta="center">
            {error}
          </Text>
        </Stack>
      </Center>
    );
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/documents" element={<Documents />} />
        <Route path="/visits" element={<Visits />} />
        <Route path="/patient" element={<PatientCard />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
