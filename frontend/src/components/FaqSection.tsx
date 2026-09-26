import FaqItem from './FaqItem';

// Lista de Perguntas
const FAQ_DATA = [
    {
        id: 1,
        question: "Pergunta 1 ?",
        answer: "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Fusce feugiat suscipit velit a placerat. Donec tincidunt est id imperdiet hendrerit. "
    },
    {
        id: 2,
        question: "Pergunta 2 ?",
        answer: "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Fusce feugiat suscipit velit a placerat. Donec tincidunt est id imperdiet hendrerit. "
    },
    {
        id: 3,
        question: "Pergunta 3?",
        answer: "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Fusce feugiat suscipit velit a placerat. Donec tincidunt est id imperdiet hendrerit. "
    }
];


export default function FaqSection() {
    return (
        <section className="w-full max-w-2xl mx-auto my-12 px-4">
            <h2 className="text-2xl text-center text-gray-900 mb-8">
                Perguntas Frequentes
            </h2>

            <div className="space-y-4">
                {FAQ_DATA.map((item) => ( 
                    <FaqItem key={item.id} question={item.question} answer={item.answer} />
                ))}
            </div>
        </section>
    );
}