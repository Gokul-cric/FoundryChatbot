import { Table } from "antd"; 

const ChatMessages = ({ messages }) => {
  return (
    <div className="chat-container">
      {messages.map((msg) => (
        <div key={msg.id} className={`message ${msg.type}`}>
          {msg.isTable ? (
            <Table
              dataSource={msg.tableData}
              columns={msg.tableColumns}
              pagination={false}
              bordered
            />
          ) : (
            <p>{msg.content}</p>
          )}
        </div>
      ))}
    </div>
  );
};

export default ChatMessages;
