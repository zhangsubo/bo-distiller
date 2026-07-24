import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface Props {
  content: string;
}

/**
 * 将涉及文章的单行链接列表转换为有序列表格式
 * 输入: - **涉及文章**: [[标题1](url1)]、[[标题2](url2)]、...
 * 输出: - **涉及文章**:\n  1. [标题1](url1)\n  2. [标题2](url2)\n...
 */
function transformArticleList(content: string): string {
  return content.replace(
    /(- \*\*涉及文章(?:列表)?\*\*:\s*)(.+)$/gm,
    (_, prefix, linksStr) => {
      // 匹配 [[标题](url)] 格式的链接（双括号）
      const linkRegex = /\[\[([^\]]+)\]\(([^)]+)\)\]/g;
      const links: { title: string; url: string }[] = [];
      let match;
      while ((match = linkRegex.exec(linksStr)) !== null) {
        links.push({ title: match[1], url: match[2] });
      }
      if (links.length === 0) return prefix + linksStr;
      // 去重（按 URL）
      const seen = new Set<string>();
      const uniqueLinks = links.filter(l => {
        if (seen.has(l.url)) return false;
        seen.add(l.url);
        return true;
      });
      // 生成有序列表
      const listItems = uniqueLinks
        .map((l, i) => `  ${i + 1}. [${l.title}](${l.url})`)
        .join('\n');
      return prefix + '\n' + listItems;
    }
  );
}

const MarkdownRenderer: React.FC<Props> = ({ content }) => {
  const transformedContent = transformArticleList(content);

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        code({ className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '');
          const isBlock = String(children).includes('\n');
          if (match && isBlock) {
            return (
              <SyntaxHighlighter
                style={oneDark}
                language={match[1]}
                PreTag="div"
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            );
          }
          return (
            <code className={className} {...props}>
              {children}
            </code>
          );
        },
        a({ href, children, ...props }) {
          return (
            <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
              {children}
            </a>
          );
        },
      }}
    >
      {transformedContent}
    </ReactMarkdown>
  );
};

export default MarkdownRenderer;
