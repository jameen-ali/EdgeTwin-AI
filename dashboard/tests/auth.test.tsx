import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { AuthProvider, useAuth } from "../src/context/AuthContext";
import { ProtectedRoute } from "../src/App";
import { api } from "../src/api/client";

const TestAuthConsumer = () => {
  const { user, isAuthenticated, login, logout, isLoading } = useAuth();
  return (
    <div>
      <div data-testid="auth-status">{isAuthenticated ? "AUTHENTICATED" : "ANONYMOUS"}</div>
      <div data-testid="username">{user?.username || "NONE"}</div>
      <div data-testid="loading-state">{isLoading ? "LOADING" : "IDLE"}</div>
      <button onClick={() => login({ username: "admin", password: "Admin123!" })}>Log In</button>
      <button onClick={logout}>Log Out</button>
    </div>
  );
};

describe("Authentication & Session Provider", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("initializes with ANONYMOUS status when no stored token", async () => {
    render(
      <AuthProvider>
        <TestAuthConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading-state")).toHaveTextContent("IDLE");
    });
    expect(screen.getByTestId("auth-status")).toHaveTextContent("ANONYMOUS");
  });

  it("authenticates and saves token upon successful login", async () => {
    vi.spyOn(api.auth, "login").mockResolvedValue({
      access_token: "mock-jwt-token-1234",
      token_type: "bearer",
      expires_in: 3600,
      role: "ADMIN",
      username: "admin",
    });

    vi.spyOn(api.auth, "getMe").mockResolvedValue({
      id: 1,
      username: "admin",
      role: "ADMIN",
      is_active: true,
      created_at: "2026-09-28T00:00:00Z",
    });

    render(
      <AuthProvider>
        <TestAuthConsumer />
      </AuthProvider>
    );

    const loginBtn = screen.getByRole("button", { name: /log in/i });
    fireEvent.click(loginBtn);

    await waitFor(() => {
      expect(screen.getByTestId("auth-status")).toHaveTextContent("AUTHENTICATED");
    });

    expect(screen.getByTestId("username")).toHaveTextContent("admin");
    expect(localStorage.getItem("edgetwin_token")).toBe("mock-jwt-token-1234");
  });

  it("clears user and token upon logout", async () => {
    localStorage.setItem("edgetwin_token", "existing-token");
    vi.spyOn(api.auth, "getMe").mockResolvedValue({
      id: 1,
      username: "admin",
      role: "ADMIN",
      is_active: true,
      created_at: "2026-09-28T00:00:00Z",
    });

    render(
      <AuthProvider>
        <TestAuthConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("auth-status")).toHaveTextContent("AUTHENTICATED");
    });

    const logoutBtn = screen.getByRole("button", { name: /log out/i });
    fireEvent.click(logoutBtn);

    expect(screen.getByTestId("auth-status")).toHaveTextContent("ANONYMOUS");
    expect(screen.getByTestId("username")).toHaveTextContent("NONE");
    expect(localStorage.getItem("edgetwin_token")).toBeNull();
  });

  it("ProtectedRoute redirects unauthenticated visitors to /login", async () => {
    render(
      <MemoryRouter initialEntries={["/protected-dashboard"]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<div data-testid="login-view">Login Page View</div>} />
            <Route
              path="/protected-dashboard"
              element={
                <ProtectedRoute>
                  <div data-testid="secret-view">Sensitive Dashboard</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId("login-view")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("secret-view")).not.toBeInTheDocument();
  });
});
