import React from "react";
import FishOneAnalyticsChatbot from "./components/FishOneAnalyticsChatbot";
import "./styles/Chatbot.css";

const App = () => {
  return (
    <div className="w-full h-screen flex flex-col items-center justify-center bg-gray-100">

      <div className="w-full h-full flex items-center justify-center">
        <FishOneAnalyticsChatbot />
      </div>
    </div>
  );
};

export default App;
