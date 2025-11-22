import { StyleSheet } from "react-native";

export const authStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0f172a",
    justifyContent: "center",
    padding: 20,
  },
  box: {
    backgroundColor: "white",
    padding: 20,
    borderRadius: 16,
    elevation: 5,
  },
  title: {
    fontSize: 22,
    fontWeight: "600",
    marginBottom: 15,
    textAlign: "center",
  },
  input: {
    backgroundColor: "#f1f5f9",
    padding: 12,
    borderRadius: 10,
    marginBottom: 12,
    fontSize: 16,
  },
  button: {
    backgroundColor: "#0f172a",
    paddingVertical: 12,
    borderRadius: 10,
    marginTop: 10,
    marginBottom: 10,
  },
  buttonText: {
    color: "white",
    fontWeight: "600",
    textAlign: "center",
    fontSize: 16,
  },
  footerText: {
    textAlign: "center",
    marginTop: 8,
    color: "#334155",
  },
  link: {
    fontWeight: "600",
    color: "#0f172a",
  },
  error: {
    color: "red",
    marginBottom: 10,
    textAlign: "center",
  },
});
