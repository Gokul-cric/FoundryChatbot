import React from "react";
import { Link } from "react-router-dom";
import "./Sidebar.css";

const Sidebar = () => {
    return (
        <div className="sidebar">
            <h2>Menu</h2>
            <ul>
                <li><Link to="/chatbot">Chatbot</Link></li>
                <li><Link to="/reports">Download Reports</Link></li>
            </ul>
        </div>
    );
};

export default Sidebar;
