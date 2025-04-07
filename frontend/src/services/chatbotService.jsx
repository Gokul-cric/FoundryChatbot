const API_URL = process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:5000";

const chatbotService = {
    askBot: async (query) => {
        try {
            const response = await fetch(`${API_URL}/chatbot/ask`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ query }),
            });

            const data = await response.json();
            return data.response || "No response from the server.";
        } catch (error) {
            console.error("Error contacting chatbot API:", error);
            return "An error occurred while fetching the response.";
        }
    },
};

export default chatbotService;
