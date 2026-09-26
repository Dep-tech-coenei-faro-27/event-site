import React, { useState } from 'react';

interface FormDataState { // Fiz com base em email para podermos retornar a mensagem...
    email: string;
    subject: string;
    message: string;
}

export default function ContactSupportForm() {
    const [formData, setFormData] = useState<FormDataState>({
        email: '', 
        subject: '',
        message: '',
    });

    const handleChange = (
        e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement> ) => { const { name, value } = e.target;
            setFormData((prev) => ({ ...prev, [name]: value, }));
    };

    const handleSubmit = (e: React.SyntheticEvent<HTMLFormElement>) => {
        e.preventDefault();
        console.log('Dados do formulário enviados:', formData);

        setFormData({
            email: '',
            subject: '',
            message: '',
        });
    };

    return (
        <>
        <h2 className="text-center text-h2">
            Contact Forms
        </h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4 mt-8">
            <div>
                <label htmlFor="email" className="block text-sm font-medium">Email</label>
                <input
                id="email"
                name="email"
                type="email"
                required
                value={formData.email}
                onChange={handleChange}
                className="border p-2 w-full rounded"
                placeholder="exemplo@email.com"
            />
            </div>

            <div>
                <label htmlFor="subject" className="block text-sm font-medium">Assunto</label>
                <input
                id="subject"
                name="subject"
                type="text"
                required
                value={formData.subject}
                onChange={handleChange}
                className="border p-2 w-full rounded"
                placeholder="Motivo do contacto"
            />
            </div>

            <div>
                <label htmlFor="message" className="block text-sm font-medium">Mensagem</label>
                <textarea
                id="message"
                name="message"
                rows={4}
                required
                value={formData.message}
                onChange={handleChange}
                className="border p-2 w-full rounded"
                placeholder="Escreve a tua mensagem aqui..."
            />
            </div>

            <button type="submit" className="bg-white border border-grey-300 py-2 px-4 hover:bg-blue-600 hover:text-white transition-colors">
                Enviar Mensagem
            </button>
    </form>
    </>
  );
}