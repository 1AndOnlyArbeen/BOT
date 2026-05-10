import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

export function RagMarkdown({ text }: { text: string }) {
  return (
    <div className="prose prose-invert max-w-none prose-pre:bg-panel2 prose-pre:border prose-pre:border-border prose-code:text-accent2 prose-code:bg-panel2 prose-code:rounded prose-code:px-1.5 prose-code:py-0.5 prose-code:text-sm">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ inline, className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || "");
            return !inline && match ? (
              <SyntaxHighlighter
                language={match[1]}
                style={oneDark as any}
                PreTag="div"
                customStyle={{ borderRadius: "8px", fontSize: "0.85rem" }}
                {...props}
              >
                {String(children).replace(/\n$/, "")}
              </SyntaxHighlighter>
            ) : (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
